# Slowest decisions -- top functions by cumulative time


## adjudicate / arc_owner (n=779, 16.499s)

(full listing: adjudicate_arc_owner.pstats.txt)

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      779    0.171    0.000   16.484    0.021 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:728(adjudicate_one)
      779    1.606    0.002    9.741    0.013 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:434(correlated_groups)
      779    0.532    0.001    6.185    0.008 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicators/ownership.py:190(adjudicate_arc_owner)
  4294066    2.847    0.000    5.931    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:529(_one_signal)
  1052079    0.558    0.000    2.851    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:382(_admit)
     2337    0.048    0.000    2.789    0.001 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:286(rows)
   998389    0.143    0.000    2.353    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:291(<genexpr>)
  1052079    0.532    0.000    2.029    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2244(quantities_in_closure)
   273666    0.143    0.000    1.756    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:301(verdict)
 10692290    1.174    0.000    1.670    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2215(closure)
  4294066    1.606    0.000    1.606    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:533(<setcomp>)
  3072269    0.606    0.000    1.377    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:484(union)
  2965547    0.382    0.000    1.276    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2245(<genexpr>)
   274445    0.076    0.000    0.938    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2165(verdict)
```


## evaluate / size_measure_rest (n=1183, 9.957s)

(full listing: evaluate_size_measure_rest.pstats.txt)

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     1183    0.021    0.000    9.920    0.008 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/consequences.py:116(size_measure_rest)
     5012    0.002    0.000    9.849    0.002 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2160(verdicts)
     9468    0.003    0.000    9.847    0.001 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2162(<genexpr>)
     9468    0.003    0.000    9.843    0.001 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2083(_ids)
     1183    0.001    0.000    9.837    0.008 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/consequences.py:96(_standing)
     1183    0.487    0.000    9.831    0.008 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2126(_descendants_ids)
     1183    1.815    0.002    6.631    0.006 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2101(_descendants_index)
   841033    2.791    0.000    4.816    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:145(from_key)
  3540719    1.373    0.000    2.710    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:120(contains)
  3540719    0.291    0.000    1.178    0.000 {built-in method builtins.all}
  8585009    0.735    0.000    1.047    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:125(<genexpr>)
   845765    0.487    0.000    0.630    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:91(__post_init__)
 14343802    0.456    0.000    0.456    0.000 {built-in method builtins.getattr}
   841033    0.422    0.000    0.422    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:149(<dictcomp>)
```


## adjudicate / duration (n=2993, 6.724s)

(full listing: adjudicate_duration.pstats.txt)

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     2993    0.029    0.000    6.721    0.002 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:728(adjudicate_one)
     2993    0.032    0.000    6.488    0.002 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicators/rhythm.py:405(adjudicate_duration)
    35033    0.038    0.000    6.089    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicate.py:286(rows)
   169010    0.058    0.000    5.821    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2083(_ids)
    48018    0.024    0.000    5.777    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2150(rows)
   141916    0.032    0.000    5.752    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2152(<genexpr>)
    30824    0.820    0.000    5.419    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:2126(_descendants_ids)
     2993    0.019    0.000    5.347    0.002 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicators/rhythm.py:284(_attached_dots)
  5966515    2.291    0.000    4.526    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:120(contains)
      646    0.006    0.000    3.100    0.005 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicators/rhythm.py:579(_rest_ruling)
     5340    0.004    0.000    2.570    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/adjudicators/rhythm.py:141(_cell_boxes)
  5966515    0.487    0.000    1.967    0.000 {built-in method builtins.all}
 14314644    1.230    0.000    1.748    0.000 /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a061ed05bd378c34f/tools/omr/staged/record.py:125(<genexpr>)
 18098628    0.574    0.000    0.574    0.000 {built-in method builtins.getattr}
```
