import { LARGE_FILE_BYTES, LARGE_FILES_URL } from '../config.js';
import { datasets, formatBytes } from '../lib/data.js';

function address(file) {
  if (LARGE_FILES_URL && file.bytes > LARGE_FILE_BYTES) return LARGE_FILES_URL + file.name;
  return `${import.meta.env.BASE_URL}datasets/${file.name}`;
}

// Download links for the data files that one or more datasets need.
export default function DatasetFiles({ keys }) {
  const files = [];
  const seen = new Set();
  for (const key of keys) {
    for (const file of datasets[key].files) {
      if (!seen.has(file.name)) {
        seen.add(file.name);
        files.push({ ...file, dataset: datasets[key].name });
      }
    }
  }
  return (
    <ul className="files">
      {files.map((file) => (
        <li key={file.name}>
          <a href={address(file)} download>
            <span className="file-name">{file.name}</span>
            <span className="file-meta">{formatBytes(file.bytes)} · download</span>
          </a>
        </li>
      ))}
    </ul>
  );
}
