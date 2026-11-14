// Site settings that change between running locally and the hosted site.

// movies.db (69 MB) and pcards.db (94 MB) are too large for the web host, which
// accepts files up to 25 MB. On the hosted site they are downloaded from a
// GitHub release instead. Paste the release's download address here, ending in
// a slash, for example:
//   https://github.com/<user>/<repository>/releases/download/datasets/
// Leave it empty to serve them from public/datasets, as when running locally.
export const LARGE_FILES_URL = '';

// Files above this size are fetched from LARGE_FILES_URL when it is set.
export const LARGE_FILE_BYTES = 25 * 1024 * 1024;
