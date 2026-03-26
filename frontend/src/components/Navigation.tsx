import { useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV_LINKS = [
  { to: '/', label: 'Dashboard' },
  { to: '/search', label: 'IMSLP Search' },
  { to: '/upload', label: 'Upload' },
];

const styles: Record<string, React.CSSProperties> = {
  nav: {
    backgroundColor: '#1a1a2e',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    padding: '0 24px',
    height: 56,
    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
    gap: 32,
  },
  brand: {
    fontSize: 20,
    fontWeight: 700,
    color: '#e2b96f',
    textDecoration: 'none',
    letterSpacing: '-0.5px',
    marginRight: 16,
  },
  linkList: {
    display: 'flex',
    gap: 8,
    listStyle: 'none',
    margin: 0,
    padding: 0,
    flex: 1,
  },
  link: (active: boolean): React.CSSProperties => ({
    color: active ? '#e2b96f' : '#c8d0dc',
    textDecoration: 'none',
    padding: '6px 14px',
    borderRadius: 6,
    fontWeight: active ? 600 : 400,
    fontSize: 14,
    backgroundColor: active ? 'rgba(226,185,111,0.12)' : 'transparent',
    transition: 'background-color 0.15s, color 0.15s',
  }),
  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginLeft: 'auto',
  },
  userName: {
    fontSize: 13,
    color: '#c8d0dc',
    maxWidth: 160,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  adminBadge: {
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: 0.5,
    padding: '2px 7px',
    borderRadius: 10,
    backgroundColor: '#e2b96f33',
    color: '#e2b96f',
    border: '1px solid #e2b96f55',
    textTransform: 'uppercase',
  },
  logoutBtn: {
    background: 'none',
    border: '1px solid #ffffff33',
    borderRadius: 5,
    color: '#c8d0dc',
    fontSize: 12,
    padding: '4px 12px',
    cursor: 'pointer',
  },
};

export default function Navigation() {
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <nav style={styles.nav}>
      <Link to="/" style={styles.brand}>
        ReEngrave
      </Link>
      <ul style={styles.linkList}>
        {NAV_LINKS.map(({ to, label }) => {
          const isActive =
            to === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(to);
          return (
            <li key={to}>
              <Link to={to} style={styles.link(isActive)}>
                {label}
              </Link>
            </li>
          );
        })}
      </ul>

      {user && (
        <div style={styles.userSection}>
          {user.role === 'admin' && (
            <span style={styles.adminBadge}>Admin</span>
          )}
          <span style={styles.userName}>{user.name ?? user.email}</span>
          <button style={styles.logoutBtn} onClick={() => logout()}>
            Log out
          </button>
        </div>
      )}
    </nav>
  );
}
