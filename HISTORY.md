# cloudpathlib Changelog

## UNRELEASED

- Added streaming I/O via `FileCacheMode.streaming` for S3, Azure Blob Storage, Google Cloud Storage, and HTTP/HTTPS. In this mode `CloudPath.open()` returns the standard `io` file objects (`BufferedReader`/`BufferedWriter`/`TextIOWrapper`) backed by ranged reads and multipart uploads instead of the local cache, so only the bytes you read are downloaded and written data is uploaded as you write it. Read streams are seekable; append and update modes fall back to the cache and remove the cache file on close. `buffering` has its builtin `open()` meaning and sets the ranged-request size (default 5 MiB). A new `streaming_max_concurrency` client option (default 4) bounds background read-ahead and part uploads per stream; the buffer size, concurrency, and multipart part size can also be set with the `CLOUDPATHLIB_STREAMING_BUFFER_SIZE`, `CLOUDPATHLIB_STREAMING_MAX_CONCURRENCY`, and `CLOUDPATHLIB_[<PROVIDER>_]STREAMING_PART_SIZE` environment variables. Opening a file for append or update in streaming mode warns that it falls back to the cache. `copy`/`rename`/`replace` stream between clients, `fspath` raises `CloudPathNotImplementedError`, and failures raise `cloudpathlib.exceptions` types including the new `CloudPathStreamingError`. See the [Streaming I/O](https://cloudpathlib.drivendata.org/stable/streaming_io/) docs. (PR [#535](https://github.com/drivendataorg/cloudpathlib/pull/535))
- Changed append mode (`a`, `ab`, `a+`, and `ab+`) to create missing cloud files, matching Python file behavior. Appending to existing files still preserves their content. (Issue [#585](https://github.com/drivendataorg/cloudpathlib/issues/585))

- Fixed mypy missing-import errors for `CloudPath` and `AnyPath` when the optional Pydantic integration is not installed. (Issue [#385](https://github.com/drivendataorg/cloudpathlib/issues/385), PR [#603](https://github.com/drivendataorg/cloudpathlib/pull/603))
- Fixed pickling a cloud path losing an explicitly configured persistent `local_cache_dir`. A path whose client was created with a `local_cache_dir` previously fell back to a fresh temporary cache directory when unpickled, so already-cached files were re-downloaded (most visibly under multiprocessing, where paths are pickled to reach workers). The explicit cache directory is now preserved across a pickle round-trip; paths that use the default/temporary cache still fall back to the default client unchanged. (Issue [#504](https://github.com/drivendataorg/cloudpathlib/issues/504))

## v0.26.0 (2026-10-01)

- Added support for Python 3.15: `CloudPath.mkdir(parent_mode=...)` works across providers, and cloud paths can be pickled repeatedly without a `ParseResult` error. (Issue [#593](https://github.com/drivendataorg/cloudpathlib/issues/593), PR [#594](https://github.com/drivendataorg/cloudpathlib/pull/594))
- Changed the minimum supported Python version from 3.9 to 3.10. **Python 3.9 is no longer supported.** (PR [#597](https://github.com/drivendataorg/cloudpathlib/pull/597))
- Changed CI so pull requests from forks no longer show failing live-test and install jobs: live cloud tests now run after a maintainer approves the run, and the Azure install check no longer needs repository secrets. (Issue [#306](https://github.com/drivendataorg/cloudpathlib/issues/306), PR [#592](https://github.com/drivendataorg/cloudpathlib/pull/592))
- Fixed a spurious `OverwriteNewerCloudError` when a write leaves the local cache file with the same modified time as the cloud file. Previously, writing the same path twice in quick succession (e.g., two `path.write_text(...)` calls) on a filesystem with coarse modified-time resolution (such as FAT/exFAT or some network mounts) could raise this error on the second close and skip the upload; these writes now upload. (PR [#586](https://github.com/drivendataorg/cloudpathlib/pull/586))
- Fixed test suite reliability issues and sped up live-backend test runs in CI. (Issue [#589](https://github.com/drivendataorg/cloudpathlib/issues/589), PRs [#586](https://github.com/drivendataorg/cloudpathlib/pull/586), [#587](https://github.com/drivendataorg/cloudpathlib/pull/587), [#588](https://github.com/drivendataorg/cloudpathlib/pull/588), [#590](https://github.com/drivendataorg/cloudpathlib/pull/590))

## v0.25.0 (2026-08-22)

- **Security fix ([GHSA-r4f8-3xc4-c8vw](https://github.com/drivendataorg/cloudpathlib/security/advisories/GHSA-r4f8-3xc4-c8vw)): local path traversal via `..` in cloud object keys.**
  Cloud object keys are opaque strings and some backends (e.g. Google Cloud Storage) accept `..`
  segments. cloudpathlib mapped keys onto local paths with plain path arithmetic and no containment
  check, so a key such as `../../evil` could escape the local cache directory (on any
  `read`/`write`/`open`/`os.fspath` of a `CloudPath`) or a download destination
  (`download_to`/`copytree`/`copy`/`move` to a local path), writing attacker-controlled bytes
  outside the intended directory. cloudpathlib now confirms each computed local target stays within
  its base directory and raises `CloudPathLocalPathTraversalError` otherwise. This guards the cache
  mapping (`CloudPath._local` and its S3/HTTP overrides), both branches of `CloudPath.download_to`
  and `CloudPath.copytree` (including joins that can escape via `\` or drive letters in keys on
  Windows), and the `cloudpathlib.local` mock's storage-side mapping. Reported by mohammad adnan
  (cystack.ps redteam).
- Added a `lazy` keyword argument to `CloudPath.walk`. By default (`lazy=False`) the existing fast behavior is preserved: the whole subtree is fetched up front with a single recursive listing. Passing `lazy=True` lists each directory on demand so that, when `top_down=True`, callers can prune subdirectories by modifying `dirnames` in-place (à la `os.walk` / `Path.walk`) to skip fetching the contents of those subtrees entirely — dramatically reducing API calls for large, sparsely-traversed trees. (Issue [#518](https://github.com/drivendataorg/cloudpathlib/issues/518), PR [#574](https://github.com/drivendataorg/cloudpathlib/pull/574))
- Added presigned URL support to the mock clients in `cloudpathlib.local`, so `as_url(presign=True)` on a `LocalS3Path`, `LocalGSPath`, or `LocalAzureBlobPath` returns a deterministic URL with `expires` and `signature` query parameters instead of raising `NotImplementedError`. This lets code that generates presigned URLs be exercised in tests that use the mock classes. (PR [#572](https://github.com/drivendataorg/cloudpathlib/pull/572))
- Fixed S3 copy and move operations to forward copy-specific extra args such as `CopySourceSSECustomerKey`, and added `addressing_style="virtual"` support for `S3Client` (Issues [#500](https://github.com/drivendataorg/cloudpathlib/issues/500), [#527](https://github.com/drivendataorg/cloudpathlib/issues/527), PR [#576](https://github.com/drivendataorg/cloudpathlib/pull/576))
- Changed `S3Client._get_metadata` to read object metadata with `HeadObject` instead of `GetObject`, so `stat`, `etag`, and `size` no longer open the object body. Also fixes a `KeyError` on `ContentLength` against S3-compatible gateways that drop `Content-Length` from `GetObject` responses. (Issue [#564](https://github.com/drivendataorg/cloudpathlib/issues/564), PR [#565](https://github.com/drivendataorg/cloudpathlib/pull/565))
- Fixed `KeyError` on `ETag` against S3-compatible gateways that omit `ETag` from `HeadObject` responses. (Issue [#582](https://github.com/drivendataorg/cloudpathlib/issues/582), PR [#583](https://github.com/drivendataorg/cloudpathlib/pull/583))
- Fixed mypy 2.x type errors in `Client` and `CloudPath` that caused CI lint failures (Issue [#563](https://github.com/drivendataorg/cloudpathlib/issues/563), PR [#566](https://github.com/drivendataorg/cloudpathlib/pull/566))
- Added `AGENTS.md` with repository-specific guidance for coding agents covering contributor
  workflow, compatibility expectations, test rig and mock usage, live backend validation, and PR
  hygiene. (PR [#573](https://github.com/drivendataorg/cloudpathlib/pull/573))

## v0.24.0 (2026-04-29)

- Added support for S3 Multi-Region Access Point (MRAP) URLs in `S3Path` (Issue [#556](https://github.com/drivendataorg/cloudpathlib/issues/556), PR [#557](https://github.com/drivendataorg/cloudpathlib/pull/557))
- Added support for Pydantic serialization (Issue [#537](https://github.com/drivendataorg/cloudpathlib/issues/537), PR [#538](https://github.com/drivendataorg/cloudpathlib/pull/538))

## v0.23.0 (2025-10-07)

- Added support for Python 3.14 (Issue [#529](https://github.com/drivendataorg/cloudpathlib/issues/529), PR [#530](https://github.com/drivendataorg/cloudpathlib/pull/530))
  - Changed `CloudPath.copy` to have the first parameter named `target` instead of `destination` and added new `follow_symlinks` and `preserve_metadata` kwargs. **Breaking change for users that relied on the first parameter being named `destination` instead of `target`.**
  - Added `CloudPath.copy_into` to copy a file or directory into another file or directory.
  - Added `CloudPath.move` to move a file or directory to another location.
  - Added `CloudPath.move_into` to move a file or directory into another file or directory.
  - Added `CloudPathInfo` and `CloudPath.info` to get information about a file or directory.
  - Added additional no-op kwargs to `mkdir`, `touch`, `glob`, `rglob`, `stat` to match pathlib.

## v0.22.0 (2025-08-29)

- Fixed issue with GS credentials, using default auth enables a wider set of authentication methods in GS (Issue [#390](https://github.com/drivendataorg/cloudpathlib/issues/390), PR [#514](https://github.com/drivendataorg/cloudpathlib/pull/514), thanks @ljyanesm) 
- Added support for http(s) urls with `HttpClient`, `HttpPath`, `HttpsClient`, and `HttpsPath`. (Issue [#455](https://github.com/drivendataorg/cloudpathlib/issues/455), PR [#468](https://github.com/drivendataorg/cloudpathlib/pull/468))
- Added experimental support for patching the builtins `open`, `os`, `os.path`, and `glob` to work with `CloudPath` objects. It is off by default; see the new "Compatibility" section in the docs for more information. (Issue [#128](https://github.com/drivendataorg/cloudpathlib/issues/128), PR [#322](https://github.com/drivendataorg/cloudpathlib/pull/322))
- Added support for `CloudPath(*parts)` to create a `CloudPath` object from a list of parts (to match `pathlib.Path`). **This is a potentially breaking change for users that relied on the second arg being the `client` instead of making it an explicit kwarg.** (PR [#322](https://github.com/drivendataorg/cloudpathlib/pull/322))

## v0.21.1 (2025-05-14)

- Fixed `rmtree` fail on Azure with no `hns` and more than 256 blobs to drop (Issue [#509](https://github.com/drivendataorg/cloudpathlib/issues/509), PR [#508](https://github.com/drivendataorg/cloudpathlib/pull/508), thanks @alikefia)

## v0.21.0 (2025-03-03)

- Removed support for deprecated env var that had a typo (`CLOUPATHLIB_FILE_CACHE_MODE`; you should use `CLOUDPATHLIB_FILE_CACHE_MODE`).
- Added support for `timeout` and `retry` kwargs for `GSClient`. (Issue [#484](https://github.com/drivendataorg/cloudpathlib/issues/484), PR [#485](https://github.com/drivendataorg/cloudpathlib/pull/485), thanks @Mchristos)
- Fixed `CloudPath(...) / other` to correctly attempt to fall back on `other`'s `__rtruediv__` implementation, in order to support classes that explicitly support the `/` with a `CloudPath` instance. Previously, this would always raise a `TypeError` if `other` were not a `str` or `PurePosixPath`. (PR [#479](https://github.com/drivendataorg/cloudpathlib/pull/479))
- Added `md5` property to `GSPath`, updated LocalGSPath to include `md5` property, updated mock_gs.MockBlob to include `md5_hash` property. (Issue [#482](https://github.com/drivendataorg/cloudpathlib/issues/482), PR [#483](https://github.com/drivendataorg/cloudpathlib/pull/453))
- Fixed an uncaught exception on Azure Gen2 storage accounts with HNS enabled when used with `DefaultAzureCredential`. (Issue [#486](https://github.com/drivendataorg/cloudpathlib/issues/486), PR [#487](https://github.com/drivendataorg/cloudpathlib/pull/487))
- Removed support for Python 3.8, which was EOL in October 2024. (PR [#502](https://github.com/drivendataorg/cloudpathlib/pull/502))

## Earlier versions

See the full changelog in the repository history (versions v0.20.0 and earlier) at https://github.com/drivendataorg/cloudpathlib/blob/master/HISTORY.md
