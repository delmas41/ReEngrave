"""
Audiveris OMR (Optical Music Recognition) integration.
Runs Audiveris as a subprocess and parses its output.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

AUDIVERIS_HOME: str = os.getenv("AUDIVERIS_HOME", "/opt/Audiveris")
# Minimum interline pixels Audiveris needs — below this, pages will be flagged invalid
_MIN_INTERLINE_PX = 12
# Target DPI for re-rendering low-res PDFs
_TARGET_DPI = 300


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AudiverisResult:
    musicxml_path: str
    book_path: str
    confidence_score: float
    measures_count: int
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_audiveris(pdf_path: str, output_dir: str) -> AudiverisResult:
    """Run Audiveris OMR on a PDF and return a structured result.

    Strategy:
      1. Prepare the PDF (upscale if needed, filter non-music pages).
      2. Try running Audiveris on the whole prepared PDF.
      3. If Audiveris refuses to export because one page threw a StepException,
         fall back to chunk mode: split into groups of CHUNK_PAGES pages and run
         Audiveris on each chunk independently, then merge the MXL output.

    Audiveris writes a .omr book file and exports MusicXML to *output_dir*.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    audiveris_bin = os.path.join(AUDIVERIS_HOME, "bin", "Audiveris")
    if not os.path.isfile(audiveris_bin):
        raise FileNotFoundError(
            f"Audiveris binary not found at {audiveris_bin}. "
            "Set AUDIVERIS_HOME environment variable."
        )

    # Prepare PDF: upscale if low-res, strip non-music pages.
    input_pdf = _ensure_adequate_resolution(pdf_path, output_dir)

    # --- attempt 0: resume from existing .omr checkpoint ---
    # Audiveris saves a .omr book file as it processes each sheet. If a previous
    # run was interrupted, we can ask Audiveris to export from that checkpoint
    # instead of re-processing everything from scratch.
    pdf_stem = Path(input_pdf).stem
    existing_omr = os.path.join(output_dir, f"{pdf_stem}.omr")
    if os.path.isfile(existing_omr):
        logger.info("Found existing .omr checkpoint — attempting export: %s", existing_omr)
        resume_result = await _run_audiveris_single(audiveris_bin, existing_omr, output_dir)
        if resume_result.musicxml_path:
            logger.info("Resumed successfully from .omr checkpoint")
            return resume_result
        logger.warning("Resume from .omr failed — falling through to full reprocess")

    # --- attempt 1: full PDF ---
    result = await _run_audiveris_single(audiveris_bin, input_pdf, output_dir)
    if result.musicxml_path:
        return result

    # --- attempt 2: chunk mode ---
    # Audiveris refuses to export if any single page throws a StepException or OOM.
    # Splitting into chunks means at most one chunk is poisoned; the rest export fine.
    # Also catches OOM errors — smaller chunks use less heap per run.
    _soft_fail_phrases = (
        "transcription did not complete",
        "Could not export",
        "could not transcribe",   # our own formatted message
        "OutOfMemoryError",       # Java heap exhausted on a complex page
        "Exit forced",            # Audiveris shutdown timeout
    )
    if any(phrase in (result.error_message or "") for phrase in _soft_fail_phrases):
        logger.warning(
            "Full-PDF Audiveris run failed to export — retrying in chunk mode"
        )
        chunk_result = await _run_audiveris_chunked(
            audiveris_bin, input_pdf, output_dir
        )
        if chunk_result.musicxml_path:
            return chunk_result
        # Merge errors from both attempts for a useful message
        result = AudiverisResult(
            musicxml_path="",
            book_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message=(
                f"Full-PDF attempt: {result.error_message} | "
                f"Chunk attempt: {chunk_result.error_message}"
            ),
        )

    return result


async def _run_audiveris_single(
    audiveris_bin: str, pdf_path: str, output_dir: str
) -> AudiverisResult:
    """Run Audiveris on a single PDF file and return whatever it produces."""
    cmd = [
        audiveris_bin,
        "-batch",
        "-export",
        "-output", output_dir,
        pdf_path,
    ]
    logger.info("Running Audiveris: %s", " ".join(cmd))

    # Give the JVM 6 GB heap. Audiveris is extremely memory-hungry on dense
    # orchestral scores — the default heap is often too small.
    env = os.environ.copy()
    env["JAVA_OPTS"] = env.get("JAVA_OPTS", "") + " -Xmx6g"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    stdout_bytes, _ = await proc.communicate()
    stdout = stdout_bytes.decode("utf-8", errors="replace")

    _soft_fails = (
        "transcription did not complete",
        "Could not export",
        "OutOfMemoryError",
        "Exit forced",
    )
    is_soft_fail = any(p in stdout for p in _soft_fails)

    if proc.returncode != 0 and not is_soft_fail:
        # Hard failure (crash, missing binary, etc.)
        return AudiverisResult(
            musicxml_path="",
            book_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message=f"Audiveris exited with code {proc.returncode}: {stdout[-500:]}",
        )

    confidence = parse_audiveris_confidence(stdout)
    pdf_stem = Path(pdf_path).stem
    book_path = os.path.join(output_dir, f"{pdf_stem}.omr")

    musicxml_path = ""
    # Check exact name first, then multi-movement exports (e.g. stem.mvt1.mxl)
    for ext in (".xml", ".mxl", ".musicxml"):
        candidate = os.path.join(output_dir, f"{pdf_stem}{ext}")
        if os.path.isfile(candidate):
            musicxml_path = candidate
            break
    if not musicxml_path:
        import glob as _glob
        mvt_files = sorted(_glob.glob(os.path.join(output_dir, f"{pdf_stem}.mvt*.*")))
        if mvt_files:
            musicxml_path = mvt_files[0]
            logger.info("Found multi-movement export: %s (%d files total)", musicxml_path, len(mvt_files))

    measures_count = 0
    if musicxml_path and validate_musicxml(musicxml_path):
        measures_count = _count_measures(musicxml_path)

    error_msg = None
    if not musicxml_path:
        if "Could not export" in stdout or "transcription did not complete" in stdout:
            error_msg = (
                "Audiveris could not transcribe this PDF. "
                "The score may be too complex or the PDF quality too low. "
                "Last output: " + stdout[-300:]
            )
        else:
            error_msg = "Audiveris produced no MusicXML output. Last output: " + stdout[-300:]

    return AudiverisResult(
        musicxml_path=musicxml_path,
        book_path=book_path if os.path.isfile(book_path) else "",
        confidence_score=confidence,
        measures_count=measures_count,
        error_message=error_msg,
    )


async def _run_audiveris_chunked(
    audiveris_bin: str, pdf_path: str, output_dir: str, chunk_size: int = 15
) -> AudiverisResult:
    """Split *pdf_path* into chunks and run Audiveris on each.

    Returns an AudiverisResult pointing at the merged MusicXML, or an error if
    no chunks produced output.
    """
    import glob
    import subprocess

    # Count pages
    try:
        result = subprocess.run(
            ["pdfinfo", pdf_path], capture_output=True, text=True, check=True
        )
        pages_match = re.search(r"Pages:\s+(\d+)", result.stdout)
        total_pages = int(pages_match.group(1)) if pages_match else 0
    except Exception:
        total_pages = 0

    if total_pages == 0:
        return AudiverisResult(
            musicxml_path="", book_path="", confidence_score=0.0,
            measures_count=0,
            error_message="Could not determine page count for chunk mode",
        )

    logger.info("Chunk mode: %d pages, chunk_size=%d", total_pages, chunk_size)

    chunk_dir = os.path.join(output_dir, "chunks")
    os.makedirs(chunk_dir, exist_ok=True)

    chunk_pdfs: list[str] = []
    try:
        from PIL import Image
        import glob as _glob

        for start in range(1, total_pages + 1, chunk_size):
            end = min(start + chunk_size - 1, total_pages)
            chunk_prefix = os.path.join(chunk_dir, f"_chunk_{start:04d}_")
            subprocess.run(
                ["pdftoppm", "-r", "300", "-png",
                 "-f", str(start), "-l", str(end),
                 pdf_path, chunk_prefix],
                capture_output=True, check=True,
            )
            chunk_pages = sorted(_glob.glob(chunk_prefix + "*.png"))
            if not chunk_pages:
                continue
            chunk_pdf = os.path.join(chunk_dir, f"chunk_{start:04d}.pdf")
            imgs = [Image.open(p).convert("RGB") for p in chunk_pages]
            imgs[0].save(
                chunk_pdf, "PDF", resolution=300,
                save_all=True, append_images=imgs[1:],
            )
            for img in imgs:
                img.close()
            for p in chunk_pages:
                try:
                    os.unlink(p)
                except OSError:
                    pass
            chunk_pdfs.append(chunk_pdf)
    except Exception as exc:
        logger.error("Chunk PDF creation failed: %s", exc)
        return AudiverisResult(
            musicxml_path="", book_path="", confidence_score=0.0,
            measures_count=0, error_message=f"Chunk PDF creation failed: {exc}",
        )

    if not chunk_pdfs:
        return AudiverisResult(
            musicxml_path="", book_path="", confidence_score=0.0,
            measures_count=0, error_message="No chunk PDFs produced",
        )

    # Run Audiveris on each chunk, checkpointing each completed chunk's MXL.
    # On retry, chunks that already have a saved MXL are skipped entirely.
    mxl_files: list[str] = []
    total_confidence = 0.0
    total_measures = 0

    for i, chunk_pdf in enumerate(chunk_pdfs):
        chunk_out = os.path.join(chunk_dir, f"out_{i:04d}")
        os.makedirs(chunk_out, exist_ok=True)

        # Check for a saved checkpoint from a previous run
        checkpoint_stem = Path(chunk_pdf).stem
        checkpoint_mxl = None
        for ext in (".mxl", ".xml", ".musicxml"):
            candidate = os.path.join(chunk_out, f"{checkpoint_stem}{ext}")
            if os.path.isfile(candidate):
                checkpoint_mxl = candidate
                break
        if not checkpoint_mxl:
            mvt_files = sorted(glob.glob(os.path.join(chunk_out, f"{checkpoint_stem}.mvt*.*")))
            if mvt_files:
                checkpoint_mxl = mvt_files[0]

        if checkpoint_mxl:
            logger.info(
                "Chunk %d/%d: reusing checkpoint %s", i + 1, len(chunk_pdfs), checkpoint_mxl
            )
            mxl_files.append(checkpoint_mxl)
            if validate_musicxml(checkpoint_mxl):
                total_measures += _count_measures(checkpoint_mxl)
            total_confidence += 0.5  # neutral confidence for resumed chunks
            continue

        logger.info("Chunk %d/%d: processing %s", i + 1, len(chunk_pdfs), chunk_pdf)
        chunk_result = await _run_audiveris_single(audiveris_bin, chunk_pdf, chunk_out)
        if chunk_result.musicxml_path:
            mxl_files.append(chunk_result.musicxml_path)
            total_confidence += chunk_result.confidence_score
            total_measures += chunk_result.measures_count
            logger.info("Chunk %d/%d: done ✓ (%d measures)", i + 1, len(chunk_pdfs), chunk_result.measures_count)
        else:
            logger.warning("Chunk %d/%d: failed — %s", i + 1, len(chunk_pdfs), chunk_result.error_message)

    if not mxl_files:
        return AudiverisResult(
            musicxml_path="", book_path="", confidence_score=0.0,
            measures_count=0,
            error_message="All chunks failed to produce MusicXML",
        )

    # Merge chunk MXL files into one
    merged_path = _merge_mxl_files(mxl_files, output_dir, Path(pdf_path).stem)
    avg_confidence = total_confidence / len(mxl_files)

    logger.info(
        "Chunk mode success: %d/%d chunks produced output, merged → %s",
        len(mxl_files), len(chunk_pdfs), merged_path,
    )
    return AudiverisResult(
        musicxml_path=merged_path,
        book_path="",
        confidence_score=avg_confidence,
        measures_count=total_measures,
        error_message=None,
    )


def _merge_mxl_files(mxl_paths: list[str], output_dir: str, stem: str) -> str:
    """Merge multiple MusicXML/MXL files into one by concatenating <part> elements.

    This is a best-effort merge: it takes the structure from the first file
    and appends the measures from subsequent files into matching parts.
    If files can't be merged cleanly, returns the first file as-is.
    """
    import zipfile
    import shutil

    def _load_xml(path: str) -> tuple[str, bytes]:
        """Return (xml_string, raw_bytes). Decompresses .mxl if needed."""
        if path.endswith(".mxl"):
            with zipfile.ZipFile(path) as z:
                for name in z.namelist():
                    if name.endswith(".xml") and not name.startswith("__"):
                        return name, z.read(name)
        with open(path, "rb") as f:
            return os.path.basename(path), f.read()

    if len(mxl_paths) == 1:
        dest = os.path.join(output_dir, f"{stem}.mxl")
        shutil.copy2(mxl_paths[0], dest)
        return dest

    try:
        # Parse all files
        trees = []
        for p in mxl_paths:
            _, raw = _load_xml(p)
            trees.append(ET.fromstring(raw))

        base = trees[0]
        ns = ""
        tag = base.tag
        if tag.startswith("{"):
            ns = tag[1: tag.index("}")]

        def _t(local: str) -> str:
            return f"{{{ns}}}{local}" if ns else local

        # Collect parts from base
        base_parts = {p.get("id"): p for p in base.findall(_t("part"))}

        for extra_tree in trees[1:]:
            for extra_part in extra_tree.findall(_t("part")):
                pid = extra_part.get("id")
                if pid in base_parts:
                    # Renumber and append measures
                    existing = base_parts[pid]
                    last_num = len(existing.findall(_t("measure")))
                    for measure in extra_part.findall(_t("measure")):
                        last_num += 1
                        measure.set("number", str(last_num))
                        existing.append(measure)

        # Write merged XML
        merged_xml = os.path.join(output_dir, f"{stem}.xml")
        ET.ElementTree(base).write(merged_xml, encoding="utf-8", xml_declaration=True)

        # Pack into .mxl
        merged_mxl = os.path.join(output_dir, f"{stem}.mxl")
        with zipfile.ZipFile(merged_mxl, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(merged_xml, f"{stem}.xml")
            z.writestr(
                "META-INF/container.xml",
                f'<?xml version="1.0"?>'
                f'<container><rootfiles>'
                f'<rootfile full-path="{stem}.xml"/>'
                f'</rootfiles></container>',
            )
        os.unlink(merged_xml)
        return merged_mxl

    except Exception as exc:
        logger.warning("MXL merge failed (%s) — returning first chunk only", exc)
        dest = os.path.join(output_dir, f"{stem}.mxl")
        import shutil
        shutil.copy2(mxl_paths[0], dest)
        return dest


def parse_audiveris_confidence(stdout: str) -> float:
    """Parse Audiveris stdout for an overall confidence score (0.0-1.0).

    Audiveris logs lines like:
        "Grade: 0.87" or "recognition: 87%"

    TODO: Update this regex when targeting a specific Audiveris version,
    as the log format varies between releases.
    """
    # Pattern 1: "Grade: 0.87"
    match = re.search(r"Grade[:\s]+([0-9]+\.?[0-9]*)", stdout, re.IGNORECASE)
    if match:
        raw = float(match.group(1))
        return min(max(raw, 0.0), 1.0)

    # Pattern 2: percentage like "87%"
    match = re.search(r"recognition[:\s]+([0-9]+)%", stdout, re.IGNORECASE)
    if match:
        return float(match.group(1)) / 100.0

    # Default: no confidence info found
    return 0.5


def validate_musicxml(xml_path: str) -> bool:
    """Check that *xml_path* is parseable XML with a MusicXML root element."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # MusicXML root tags: <score-partwise> or <score-timewise>
        tag = root.tag.lower()
        return "score" in tag
    except ET.ParseError:
        return False
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _count_measures(xml_path: str) -> int:
    """Count the number of <measure> elements in a MusicXML file."""
    try:
        tree = ET.parse(xml_path)
        # TODO: Handle timewise vs partwise MusicXML differently
        return len(tree.findall(".//{http://www.musicxml.org/musicxml}measure") or
                   tree.findall(".//measure"))
    except Exception:
        return 0


def _ensure_adequate_resolution(pdf_path: str, output_dir: str) -> str:
    """Prepare a PDF for Audiveris by:
      1. Detecting and removing non-music pages (title, blank, text-only pages)
         that Audiveris would flag as invalid and block the whole export.
      2. Upscaling small-format PDFs (pocket scores, miniature editions) by
         doubling the physical page size so Audiveris renders at 2x the pixel
         density — needed when stave interline < 12 px at native resolution.

    Returns the path to the prepared PDF (may be the original if no changes needed).
    """
    import glob
    import subprocess

    try:
        from PIL import Image

        # ------------------------------------------------------------------ #
        # Step 1 — detect page size and interline estimate
        # ------------------------------------------------------------------ #
        # Render page 2 at 150 DPI to sample a likely music page cheaply.
        # (Page 1 is often a title page; using page 2 avoids false negatives.)
        sample_prefix = os.path.join(output_dir, "_sample_p2")
        subprocess.run(
            ["pdftoppm", "-r", "150", "-png", "-f", "2", "-l", "2",
             pdf_path, sample_prefix],
            capture_output=True,
        )
        sample_files = sorted(glob.glob(sample_prefix + "*.png"))
        if sample_files:
            img = Image.open(sample_files[0]).convert("L")
            width_150, height_150 = img.size
            img.close()
            for f in sample_files:
                try:
                    os.unlink(f)
                except OSError:
                    pass
        else:
            width_150, height_150 = 0, 0

        # Physical page width in inches = px_at_150dpi / 150
        page_width_inches = width_150 / 150 if width_150 else 0

        # Audiveris renders at ~300 DPI. Estimated pixel width at Audiveris render:
        audiveris_render_px = page_width_inches * 300 if page_width_inches else 1449

        # Estimated interline (px) — empirical: interline ≈ render_px / 180
        # for a typical 2-system orchestral page. Minimum Audiveris needs: 12 px.
        estimated_interline = audiveris_render_px / 180

        needs_upscale = estimated_interline < 12 or page_width_inches < 6

        logger.info(
            "PDF page width: %.2f in | Audiveris render ~%d px | "
            "estimated interline ~%.1f px | needs_upscale=%s",
            page_width_inches, int(audiveris_render_px), estimated_interline, needs_upscale,
        )

        # ------------------------------------------------------------------ #
        # Step 2 — render all pages (at 2x if needed, else 150 DPI for detection)
        # ------------------------------------------------------------------ #
        # We always re-render to filter out non-music pages. The render DPI is
        # chosen so that Audiveris sees ≥ 16 px interline after its own rendering.
        #
        # Audiveris render px ≈ page_width_in * 300.
        # We want: (render_dpi / 150) * (audiveris_render_px / 180) ≥ 16
        # Simplest rule: if page < 6 in wide → render at 600 DPI and claim 300 DPI
        # physical size (doubles the apparent page size for Audiveris).
        if needs_upscale:
            render_dpi = 600          # produces 2x pixels
            save_resolution = 300     # tells PIL these pixels are 300 DPI → 2x physical size
        else:
            render_dpi = 300
            save_resolution = 300

        render_prefix = os.path.join(output_dir, "_render_page")
        subprocess.run(
            ["pdftoppm", "-r", str(render_dpi), "-png", pdf_path, render_prefix],
            capture_output=True, check=True,
        )
        all_pages = sorted(glob.glob(render_prefix + "*.png"))
        if not all_pages:
            logger.warning("pdftoppm produced no pages — using original PDF")
            return pdf_path

        # ------------------------------------------------------------------ #
        # Step 3 — filter out non-music pages
        # ------------------------------------------------------------------ #
        # A music page has many long horizontal dark runs (staff lines).
        # We count rows where ≥ 55% of pixels are dark, looking for ≥ 8 such rows.
        import numpy as np

        music_pages = []
        for png_path in all_pages:
            try:
                img = Image.open(png_path).convert("L")
                arr = np.asarray(img)
                dark_per_row = np.sum(arr < 128, axis=1)
                threshold = int(arr.shape[1] * 0.55)
                dark_rows = int(np.sum(dark_per_row >= threshold))
                img.close()
                if dark_rows >= 8:
                    music_pages.append(png_path)
                else:
                    logger.info("Skipping non-music page: %s (%d dark rows)", png_path, dark_rows)
            except Exception as exc:
                logger.warning("Could not analyse %s: %s", png_path, exc)
                music_pages.append(png_path)  # include it to be safe

        if not music_pages:
            logger.warning("No music pages detected — falling back to all pages")
            music_pages = all_pages

        logger.info(
            "Music pages: %d / %d total", len(music_pages), len(all_pages)
        )

        # ------------------------------------------------------------------ #
        # Step 4 — build the output PDF
        # ------------------------------------------------------------------ #
        out_path = os.path.join(output_dir, Path(pdf_path).stem + "_prepared.pdf")
        # Save pages sequentially to avoid loading all into RAM at once.
        first_img = Image.open(music_pages[0]).convert("RGB")

        def _page_generator():
            for p in music_pages[1:]:
                img = Image.open(p).convert("RGB")
                yield img
                img.close()

        first_img.save(
            out_path,
            "PDF",
            resolution=save_resolution,
            save_all=True,
            append_images=_page_generator(),
        )
        first_img.close()

        # Clean up temporary render PNGs
        for f in all_pages:
            try:
                os.unlink(f)
            except OSError:
                pass

        logger.info(
            "Prepared PDF → %s (%d music pages, render=%d DPI, save_res=%d)",
            out_path, len(music_pages), render_dpi, save_resolution,
        )
        return out_path

    except subprocess.CalledProcessError as exc:
        logger.warning("Prepare PDF subprocess failed: %s — using original", exc.stderr)
        return pdf_path
    except Exception as exc:
        logger.warning("Could not prepare PDF: %s — using original", exc)
        return pdf_path
