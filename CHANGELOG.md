# Changelog

## [0.7.0](https://github.com/TobySuch/earlybird/compare/v0.6.3...v0.7.0) (2026-04-11)


### Features

* **auth:** add change password page ([#35](https://github.com/TobySuch/earlybird/issues/35)) ([0f2248b](https://github.com/TobySuch/earlybird/commit/0f2248bf65d324949a82bf6180a31656f73790c7))
* **tracing:** add optional MLflow tracing for LLM calls ([#36](https://github.com/TobySuch/earlybird/issues/36)) ([0cfeff4](https://github.com/TobySuch/earlybird/commit/0cfeff46e3cf75df0a01d794efa619b6115474fc))


### Bug Fixes

* **docker:** invoke venv binary directly to avoid uv run syncing dev deps on startup ([#32](https://github.com/TobySuch/earlybird/issues/32)) ([f22824a](https://github.com/TobySuch/earlybird/commit/f22824aaf65799f4c1470457e37e3b9546b367e9))
* **startup:** warn only when no LLM API key is set ([#34](https://github.com/TobySuch/earlybird/issues/34)) ([6c32686](https://github.com/TobySuch/earlybird/commit/6c32686926879c05403b90f504f3beb07d3c9be9))

## [0.6.3](https://github.com/TobySuch/earlybird/compare/v0.6.2...v0.6.3) (2026-04-11)


### Bug Fixes

* **feed:** fix RSS feed compatibility with Apple Podcasts ([#30](https://github.com/TobySuch/earlybird/issues/30)) ([7dc1938](https://github.com/TobySuch/earlybird/commit/7dc19386f9d978d3bd7e1b1137adbf3e8461422d))

## [0.6.2](https://github.com/TobySuch/earlybird/compare/v0.6.1...v0.6.2) (2026-04-11)


### Bug Fixes

* **auth:** resolve Gmail OAuth redirect_uri mismatch behind reverse proxy ([#28](https://github.com/TobySuch/earlybird/issues/28)) ([39c99f5](https://github.com/TobySuch/earlybird/commit/39c99f5d97d7bdf063029650cb1468d1c00962a8))

## [0.6.1](https://github.com/TobySuch/earlybird/compare/v0.6.0...v0.6.1) (2026-04-11)


### Bug Fixes

* **docker:** copy full static/ dir in frontend stage to include favicon assets ([db67e21](https://github.com/TobySuch/earlybird/commit/db67e218141268488e68759b99a38e45ccdea3e7))

## [0.6.0](https://github.com/TobySuch/earlybird/compare/v0.5.1...v0.6.0) (2026-04-11)


### Features

* **branding:** add logo, favicon set, and nav branding ([#25](https://github.com/TobySuch/earlybird/issues/25)) ([5d40bb2](https://github.com/TobySuch/earlybird/commit/5d40bb2b9769346ea3c1614b687d86531574f588))

## [0.5.1](https://github.com/TobySuch/earlybird/compare/v0.5.0...v0.5.1) (2026-04-11)


### Bug Fixes

* **settings:** add margin under podcast feed section and fix nested form ([#23](https://github.com/TobySuch/earlybird/issues/23)) ([da4d8e2](https://github.com/TobySuch/earlybird/commit/da4d8e212d3cd27de6b7c567aa2f1b879d7d92e5))

## [0.5.0](https://github.com/TobySuch/earlybird/compare/v0.4.0...v0.5.0) (2026-04-06)


### Features

* **feed:** add RSS podcast feed ([#20](https://github.com/TobySuch/earlybird/issues/20)) ([b11079b](https://github.com/TobySuch/earlybird/commit/b11079b1979684912b241d782f9630dfe1088fd4))
* **tts:** add voice instructions field for OpenAI-compat TTS ([#18](https://github.com/TobySuch/earlybird/issues/18)) ([46e00b5](https://github.com/TobySuch/earlybird/commit/46e00b5e39d2420f03de9c8fa884f41b916b9f85))


### Documentation

* **changelog:** fix inflated v0.4.0 entries and update compare links ([e2b85ea](https://github.com/TobySuch/earlybird/commit/e2b85ea168e425a024f7946efa67826000aac1ef))

## [0.4.0](https://github.com/TobySuch/earlybird/compare/v0.3.0...v0.4.0) (2026-04-06)


### Continuous Integration

* **docker:** build multi-arch image and add major version tag ([#14](https://github.com/TobySuch/earlybird/issues/14)) ([d24ebc5](https://github.com/TobySuch/earlybird/commit/d24ebc5823faaf2e0f84c4fa6d3977e386a3f2c8))

## [0.3.0](https://github.com/TobySuch/earlybird/compare/v0.2.0...v0.3.0) (2026-04-06)


### Features

* **dashboard:** add Check inbox button to count unprocessed Gmail emails ([#11](https://github.com/TobySuch/earlybird/issues/11)) ([064a84b](https://github.com/TobySuch/earlybird/commit/064a84ba04458fb7d788b13bb792a493097f25fb))
* **llm:** add OpenAI-compatible API provider ([df9a2bf](https://github.com/TobySuch/earlybird/commit/df9a2bfc3c81916fa0444548cc79e931981f6a4f))
* **llm:** add OpenRouter attribution headers to all LLM providers ([#10](https://github.com/TobySuch/earlybird/issues/10)) ([6ee98ff](https://github.com/TobySuch/earlybird/commit/6ee98ffb5e2ada477892c5b8ec0f9ab47bd7a4d9))
* **tts:** add pluggable TTS provider with OpenAI-compatible support ([7ec1b60](https://github.com/TobySuch/earlybird/commit/7ec1b60b619982f7409d936fa2ca22ecb2b96182))


### Bug Fixes

* **pipeline:** defer Gmail processed label until full pipeline succeeds ([12851e2](https://github.com/TobySuch/earlybird/commit/12851e2f639dec804212f23b745fd044f10e39e3))

## [0.2.0](https://github.com/TobySuch/earlybird/releases/tag/v0.2.0) (2026-04-01)


### Features

* **auth:** add single-user authentication ([6a68fee](https://github.com/TobySuch/earlybird/commit/6a68feebe9636cbc264fd6207e9397f79dac4338))
* **db:** add Alembic migrations ([324e6db](https://github.com/TobySuch/earlybird/commit/324e6dbe736384802025f179cb7bcd3a3dc84291))
* **frontend:** upgrade Tailwind CSS v3 → v4 ([ac7870c](https://github.com/TobySuch/earlybird/commit/ac7870c258a66dcf6f6d9cfe044d6bfb6494b2e3))
* **ingest:** implement Gmail OAuth2 auth and email ingestion ([57870ae](https://github.com/TobySuch/earlybird/commit/57870ae608bc005c36ce7f7f6dead8d0efa01401))
* **pipeline:** implement ElevenLabs TTS podcast generation ([dde86cc](https://github.com/TobySuch/earlybird/commit/dde86ccd39bfd0b7251bf7d5688029f9604e91af))
* **pipeline:** implement LLM summarisation with pluggable provider interface ([9eb93c0](https://github.com/TobySuch/earlybird/commit/9eb93c0891276c14e4d13f50359f489203704bc2))
* **pipeline:** wire up run trigger, per-run logging, and run detail UI ([3de7f39](https://github.com/TobySuch/earlybird/commit/3de7f3934fd10ba28d40c2a3d04408de2308ea51))
* **project:** initial project scaffold ([531c9f7](https://github.com/TobySuch/earlybird/commit/531c9f7b8d19b3e4e10d6b002e41373fce7d99cf))
* **settings:** add schedule enable/disable toggle ([ac03012](https://github.com/TobySuch/earlybird/commit/ac030121f3791e004379a7c88d8833dfb8c17dbf))
* **ui:** add episode permalink view at /episodes/{id} ([49b6dea](https://github.com/TobySuch/earlybird/commit/49b6deae8d22da8b606c10ccb528fa3466a8bbe5))
* **ui:** add latest episode link to dashboard episodes card ([3cafe5a](https://github.com/TobySuch/earlybird/commit/3cafe5a0dc13a32c05a345706a06b444bd262ffe))
* **ui:** add podcast player to episodes list and fix Firefox range input ([90d1fe3](https://github.com/TobySuch/earlybird/commit/90d1fe3aa40b2fc5e651e7e1524c9b14ddc237cb))
* **ui:** poll running status every 5s via HTMX partials ([624924a](https://github.com/TobySuch/earlybird/commit/624924aea358b98f9ae65839276e8539574937f8))
* **ui:** replace dashboard stats with side-by-side cards ([5078cf1](https://github.com/TobySuch/earlybird/commit/5078cf1a0cf282d77ec78bbad094b8b0d1bc2c23))
* **ui:** wire up episodes and settings pages ([1c80eda](https://github.com/TobySuch/earlybird/commit/1c80eda22bbeff361861b9003f6ed91a728bb991))


### Bug Fixes

* **ci:** add token to checkout step for commitlint action ([44a761d](https://github.com/TobySuch/earlybird/commit/44a761d5f475e96511350a278cb9fa0051ff200f))
* **ci:** add token to checkout step for commitlint action ([dcab29d](https://github.com/TobySuch/earlybird/commit/dcab29d6bcd7515654760f7b8e6bb6b33d6cc51a))
* **ci:** fix Dependabot PR failures — commitlint permissions and test DB ([303097a](https://github.com/TobySuch/earlybird/commit/303097a89e30706044c3e3a903d2a6df64aa7031))
* **ci:** skip commitlint for Dependabot PRs ([570d9df](https://github.com/TobySuch/earlybird/commit/570d9df64676777489785345c4890444b2fd4f0e))
* **db:** handle empty alembic_version table and restore startup logging ([8789bf3](https://github.com/TobySuch/earlybird/commit/8789bf307af18f0f58ae6f06197d1f054c6dfbdf))
* **docker:** copy alembic.ini and migrations into image ([402fa65](https://github.com/TobySuch/earlybird/commit/402fa656597998f4cd54a60ff3b9efdbea449b52))
* **pipeline:** skip empty newsletters and exit early when none found ([2e641b9](https://github.com/TobySuch/earlybird/commit/2e641b907eefba1772e14ae6f11940314ed8600e))
* **ui:** add cursor-pointer to all interactive elements ([0c163ed](https://github.com/TobySuch/earlybird/commit/0c163ed0986774d2aa547b4aba59138b08d527f0))
* **ui:** display newsletters_found in run log table ([6559e36](https://github.com/TobySuch/earlybird/commit/6559e36b092a24f63090e2d058256c2a9cde8f8f))
* **ui:** fix audio widget duration not loading ([e21c2ad](https://github.com/TobySuch/earlybird/commit/e21c2ad86c0be028d32f269afc29cf1ce8995368))
* **ui:** fix episode accordion collapse and improve timestamp ([08fe5bf](https://github.com/TobySuch/earlybird/commit/08fe5bf3b18ab8be04d460cf87877a0253704f4e))
