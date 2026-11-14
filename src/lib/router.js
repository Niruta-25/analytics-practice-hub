// Minimal hash router: every exam and question has its own address
// (for example #/exams/E017), and the browser's Back button works.
import { useEffect, useState } from 'react';

function read() {
  const path = window.location.hash.replace(/^#\/?/, '');
  return path.split('/').filter(Boolean).map(decodeURIComponent);
}

export function useRoute() {
  const [parts, setParts] = useState(read);
  useEffect(() => {
    const onChange = () => {
      setParts(read());
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return parts;
}

export function href(...parts) {
  return `#/${parts.map(encodeURIComponent).join('/')}`;
}

export function go(...parts) {
  window.location.hash = href(...parts);
}
