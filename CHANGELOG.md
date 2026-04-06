# Changelog

## [0.5.0](https://github.com/TobySuch/earlybird/compare/v0.4.0...v0.5.0) (2026-04-06)


### Features

* **auth:** add single-user authentication ([6a68fee](https://github.com/TobySuch/earlybird/commit/6a68feebe9636cbc264fd6207e9397f79dac4338))
* **dashboard:** add Check inbox button to count unprocessed Gmail emails ([#11](https://github.com/TobySuch/earlybird/issues/11)) ([064a84b](https://github.com/TobySuch/earlybird/commit/064a84ba04458fb7d788b13bb792a493097f25fb))
* **db:** add Alembic migrations ([324e6db](https://github.com/TobySuch/earlybird/commit/324e6dbe736384802025f179cb7bcd3a3dc84291))
* **frontend:** upgrade Tailwind CSS v3 → v4 ([ac7870c](https://github.com/TobySuch/earlybird/commit/ac7870c258a66dcf6f6d9cfe044d6bfb6494b2e3))
* **ingest:** implement Gmail OAuth2 auth and email ingestion ([57870ae](https://github.com/TobySuch/earlybird/commit/57870ae608bc005c36ce7f7f6dead8d0efa01401))
* **llm:** add OpenAI-compatible API provider ([df9a2bf](https://github.com/TobySuch/earlybird/commit/df9a2bfc3c81916fa0444548cc79e931981f6a4f))
* **llm:** add OpenRouter attribution headers to all LLM providers ([#10](https://github.com/TobySuch/earlybird/issues/10)) ([6ee98ff](https://github.com/TobySuch/earlybird/commit/6ee98ffb5e2ada477892c5b8ec0f9ab47bd7a4d9))
* **pipeline:** implement ElevenLabs TTS podcast generation ([dde86cc](https://github.com/TobySuch/earlybird/commit/dde86ccd39bfd0b7251bf7d5688029f9604e91af))
* **pipeline:** implement LLM summarisation with pluggable provider interface ([9eb93c0](https://github.com/TobySuch/earlybird/commit/9eb93c0891276c14e4d13f50359f489203704bc2))
* **pipeline:** wire up run trigger, per-run logging, and run detail UI ([3de7f39](https://github.com/TobySuch/earlybird/commit/3de7f3934fd10ba28d40c2a3d04408de2308ea51))
* **project:** initial project scaffold ([531c9f7](https://github.com/TobySuch/earlybird/commit/531c9f7b8d19b3e4e10d6b002e41373fce7d99cf))
* **settings:** add schedule enable/disable toggle ([ac03012](https://github.com/TobySuch/earlybird/commit/ac030121f3791e004379a7c88d8833dfb8c17dbf))
* **tts:** add pluggable TTS provider with OpenAI-compatible support ([7ec1b60](https://github.com/TobySuch/earlybird/commit/7ec1b60b619982f7409d936fa2ca22ecb2b96182))
* **tts:** add voice instructions field for OpenAI-compat TTS ([#18](https://github.com/TobySuch/earlybird/issues/18)) ([46e00b5](https://github.com/TobySuch/earlybird/commit/46e00b5e39d2420f03de9c8fa884f41b916b9f85))
* **ui:** add episode permalink view at /episodes/{id} ([49b6dea](https://github.com/TobySuch/earlybird/commit/49b6deae8d22da8b606c10ccb528fa3466a8bbe5))
* **ui:** add latest episode link to dashboard episodes card ([3cafe5a](https://github.com/TobySuch/earlybird/commit/3cafe5a0dc13a32c05a345706a06b444bd262ffe))
* **ui:** add podcast player to episodes list and fix Firefox range input ([90d1fe3](https://github.com/TobySuch/earlybird/commit/90d1fe3aa40b2fc5e651e7e1524c9b14ddc237cb))
* **ui:** poll running status every 5s via HTMX partials ([624924a](https://github.com/TobySuch/earlybird/commit/624924aea358b98f9ae65839276e8539574937f8))
* **ui:** replace dashboard stats with side-by-side cards ([5078cf1](https://github.com/TobySuch/earlybird/commit/5078cf1a0cf282d77ec78bbad094b8b0d1bc2c23))
* **ui:** replace dashboard stats with side-by-side cards ([a347ca9](https://github.com/TobySuch/earlybird/commit/a347ca9c3371fcac7a4ce59eb9d1d111bc882bec))
* **ui:** wire up episodes and settings pages ([1c80eda](https://github.com/TobySuch/earlybird/commit/1c80eda22bbeff361861b9003f6ed91a728bb991))


### Bug Fixes

* **ci:** add token to checkout step for commitlint action ([44a761d](https://github.com/TobySuch/earlybird/commit/44a761d5f475e96511350a278cb9fa0051ff200f))
* **ci:** add token to checkout step for commitlint action ([dcab29d](https://github.com/TobySuch/earlybird/commit/dcab29d6bcd7515654760f7b8e6bb6b33d6cc51a))
* **ci:** fix Dependabot PR failures — commitlint permissions and test DB ([303097a](https://github.com/TobySuch/earlybird/commit/303097a89e30706044c3e3a903d2a6df64aa7031))
* **ci:** skip commitlint for Dependabot PRs ([570d9df](https://github.com/TobySuch/earlybird/commit/570d9df64676777489785345c4890444b2fd4f0e))
* **db:** handle empty alembic_version table and restore startup logging ([8789bf3](https://github.com/TobySuch/earlybird/commit/8789bf307af18f0f58ae6f06197d1f054c6dfbdf))
* **docker:** copy alembic.ini and migrations into image ([402fa65](https://github.com/TobySuch/earlybird/commit/402fa656597998f4cd54a60ff3b9efdbea449b52))
* **pipeline:** defer Gmail processed label until full pipeline succeeds ([12851e2](https://github.com/TobySuch/earlybird/commit/12851e2f639dec804212f23b745fd044f10e39e3))
* **pipeline:** skip empty newsletters and exit early when none found ([2e641b9](https://github.com/TobySuch/earlybird/commit/2e641b907eefba1772e14ae6f11940314ed8600e))
* **ui:** add cursor-pointer to all interactive elements ([0c163ed](https://github.com/TobySuch/earlybird/commit/0c163ed0986774d2aa547b4aba59138b08d527f0))
* **ui:** display newsletters_found in run log table ([6559e36](https://github.com/TobySuch/earlybird/commit/6559e36b092a24f63090e2d058256c2a9cde8f8f))
* **ui:** fix audio widget duration not loading ([e21c2ad](https://github.com/TobySuch/earlybird/commit/e21c2ad86c0be028d32f269afc29cf1ce8995368))
* **ui:** fix episode accordion collapse and improve timestamp ([08fe5bf](https://github.com/TobySuch/earlybird/commit/08fe5bf3b18ab8be04d460cf87877a0253704f4e))

## [0.4.0](https://github.com/TobySuch/earlybird/compare/earlybird-v0.3.0...earlybird-v0.4.0) (2026-04-06)


### Features

* **auth:** add single-user authentication ([6a68fee](https://github.com/TobySuch/earlybird/commit/6a68feebe9636cbc264fd6207e9397f79dac4338))
* **dashboard:** add Check inbox button to count unprocessed Gmail emails ([#11](https://github.com/TobySuch/earlybird/issues/11)) ([064a84b](https://github.com/TobySuch/earlybird/commit/064a84ba04458fb7d788b13bb792a493097f25fb))
* **db:** add Alembic migrations ([324e6db](https://github.com/TobySuch/earlybird/commit/324e6dbe736384802025f179cb7bcd3a3dc84291))
* **frontend:** upgrade Tailwind CSS v3 → v4 ([ac7870c](https://github.com/TobySuch/earlybird/commit/ac7870c258a66dcf6f6d9cfe044d6bfb6494b2e3))
* **ingest:** implement Gmail OAuth2 auth and email ingestion ([57870ae](https://github.com/TobySuch/earlybird/commit/57870ae608bc005c36ce7f7f6dead8d0efa01401))
* **llm:** add OpenAI-compatible API provider ([df9a2bf](https://github.com/TobySuch/earlybird/commit/df9a2bfc3c81916fa0444548cc79e931981f6a4f))
* **llm:** add OpenRouter attribution headers to all LLM providers ([#10](https://github.com/TobySuch/earlybird/issues/10)) ([6ee98ff](https://github.com/TobySuch/earlybird/commit/6ee98ffb5e2ada477892c5b8ec0f9ab47bd7a4d9))
* **pipeline:** implement ElevenLabs TTS podcast generation ([dde86cc](https://github.com/TobySuch/earlybird/commit/dde86ccd39bfd0b7251bf7d5688029f9604e91af))
* **pipeline:** implement LLM summarisation with pluggable provider interface ([9eb93c0](https://github.com/TobySuch/earlybird/commit/9eb93c0891276c14e4d13f50359f489203704bc2))
* **pipeline:** wire up run trigger, per-run logging, and run detail UI ([3de7f39](https://github.com/TobySuch/earlybird/commit/3de7f3934fd10ba28d40c2a3d04408de2308ea51))
* **project:** initial project scaffold ([531c9f7](https://github.com/TobySuch/earlybird/commit/531c9f7b8d19b3e4e10d6b002e41373fce7d99cf))
* **settings:** add schedule enable/disable toggle ([ac03012](https://github.com/TobySuch/earlybird/commit/ac030121f3791e004379a7c88d8833dfb8c17dbf))
* **tts:** add pluggable TTS provider with OpenAI-compatible support ([7ec1b60](https://github.com/TobySuch/earlybird/commit/7ec1b60b619982f7409d936fa2ca22ecb2b96182))
* **ui:** add episode permalink view at /episodes/{id} ([49b6dea](https://github.com/TobySuch/earlybird/commit/49b6deae8d22da8b606c10ccb528fa3466a8bbe5))
* **ui:** add latest episode link to dashboard episodes card ([3cafe5a](https://github.com/TobySuch/earlybird/commit/3cafe5a0dc13a32c05a345706a06b444bd262ffe))
* **ui:** add podcast player to episodes list and fix Firefox range input ([90d1fe3](https://github.com/TobySuch/earlybird/commit/90d1fe3aa40b2fc5e651e7e1524c9b14ddc237cb))
* **ui:** poll running status every 5s via HTMX partials ([624924a](https://github.com/TobySuch/earlybird/commit/624924aea358b98f9ae65839276e8539574937f8))
* **ui:** replace dashboard stats with side-by-side cards ([5078cf1](https://github.com/TobySuch/earlybird/commit/5078cf1a0cf282d77ec78bbad094b8b0d1bc2c23))
* **ui:** replace dashboard stats with side-by-side cards ([a347ca9](https://github.com/TobySuch/earlybird/commit/a347ca9c3371fcac7a4ce59eb9d1d111bc882bec))
* **ui:** wire up episodes and settings pages ([1c80eda](https://github.com/TobySuch/earlybird/commit/1c80eda22bbeff361861b9003f6ed91a728bb991))


### Bug Fixes

* **ci:** add token to checkout step for commitlint action ([44a761d](https://github.com/TobySuch/earlybird/commit/44a761d5f475e96511350a278cb9fa0051ff200f))
* **ci:** add token to checkout step for commitlint action ([dcab29d](https://github.com/TobySuch/earlybird/commit/dcab29d6bcd7515654760f7b8e6bb6b33d6cc51a))
* **ci:** fix Dependabot PR failures — commitlint permissions and test DB ([303097a](https://github.com/TobySuch/earlybird/commit/303097a89e30706044c3e3a903d2a6df64aa7031))
* **ci:** skip commitlint for Dependabot PRs ([570d9df](https://github.com/TobySuch/earlybird/commit/570d9df64676777489785345c4890444b2fd4f0e))
* **db:** handle empty alembic_version table and restore startup logging ([8789bf3](https://github.com/TobySuch/earlybird/commit/8789bf307af18f0f58ae6f06197d1f054c6dfbdf))
* **docker:** copy alembic.ini and migrations into image ([402fa65](https://github.com/TobySuch/earlybird/commit/402fa656597998f4cd54a60ff3b9efdbea449b52))
* **pipeline:** defer Gmail processed label until full pipeline succeeds ([12851e2](https://github.com/TobySuch/earlybird/commit/12851e2f639dec804212f23b745fd044f10e39e3))
* **pipeline:** skip empty newsletters and exit early when none found ([2e641b9](https://github.com/TobySuch/earlybird/commit/2e641b907eefba1772e14ae6f11940314ed8600e))
* **ui:** add cursor-pointer to all interactive elements ([0c163ed](https://github.com/TobySuch/earlybird/commit/0c163ed0986774d2aa547b4aba59138b08d527f0))
* **ui:** display newsletters_found in run log table ([6559e36](https://github.com/TobySuch/earlybird/commit/6559e36b092a24f63090e2d058256c2a9cde8f8f))
* **ui:** fix audio widget duration not loading ([e21c2ad](https://github.com/TobySuch/earlybird/commit/e21c2ad86c0be028d32f269afc29cf1ce8995368))
* **ui:** fix episode accordion collapse and improve timestamp ([08fe5bf](https://github.com/TobySuch/earlybird/commit/08fe5bf3b18ab8be04d460cf87877a0253704f4e))

## [0.3.0](https://github.com/TobySuch/earlybird/compare/earlybird-v0.2.0...earlybird-v0.3.0) (2026-04-06)


### Features

* **dashboard:** add Check inbox button to count unprocessed Gmail emails ([#11](https://github.com/TobySuch/earlybird/issues/11)) ([91d6f5a](https://github.com/TobySuch/earlybird/commit/91d6f5a2a9afb8dcb547bfd54ab034a661dd7074))
* **llm:** add OpenAI-compatible API provider ([945888b](https://github.com/TobySuch/earlybird/commit/945888bff1b6f6d0a163cf8ff19d1bf19c5e6b50))
* **llm:** add OpenRouter attribution headers to all LLM providers ([#10](https://github.com/TobySuch/earlybird/issues/10)) ([075a525](https://github.com/TobySuch/earlybird/commit/075a525c056dce27d433e3293b00c211b9ccc9a3))
* **tts:** add pluggable TTS provider with OpenAI-compatible support ([3b26af4](https://github.com/TobySuch/earlybird/commit/3b26af4fa37c25cf1bb7ae3d71d7f8d537a2cdcf))


### Bug Fixes

* **pipeline:** defer Gmail processed label until full pipeline succeeds ([4e17710](https://github.com/TobySuch/earlybird/commit/4e17710bede19186b28ac43fea2346a8d1c7add1))

## [0.2.0](https://github.com/TobySuch/earlybird/compare/earlybird-v0.1.0...earlybird-v0.2.0) (2026-04-01)


### Features

* **auth:** add single-user authentication ([3d1fa03](https://github.com/TobySuch/earlybird/commit/3d1fa0330d94d2cc46ad223a1f872108f3e09321))
* **db:** add Alembic migrations ([91ff353](https://github.com/TobySuch/earlybird/commit/91ff3535baec3997d35fee7071e43ca75f32f511))
* **frontend:** upgrade Tailwind CSS v3 → v4 ([8d36f24](https://github.com/TobySuch/earlybird/commit/8d36f247d7f44c9ece1c3c7dc37aafeb72d3f48a))
* **ingest:** implement Gmail OAuth2 auth and email ingestion ([3ca2926](https://github.com/TobySuch/earlybird/commit/3ca2926d9cca39374c6fb23d3d56ee30ef6c38c3))
* **pipeline:** implement ElevenLabs TTS podcast generation ([5a0b360](https://github.com/TobySuch/earlybird/commit/5a0b36062d2990fada6a28e55906704b5dae491f))
* **pipeline:** implement LLM summarisation with pluggable provider interface ([1d8db4c](https://github.com/TobySuch/earlybird/commit/1d8db4c7298efff0a60ef872eabfd1ff61bdc94d))
* **pipeline:** wire up run trigger, per-run logging, and run detail UI ([0c70a35](https://github.com/TobySuch/earlybird/commit/0c70a35c65801bbbd1a02268fa71098d0ee8a4e7))
* **project:** initial project scaffold ([bd96a36](https://github.com/TobySuch/earlybird/commit/bd96a366c4b9cb35664079657baaf8eaa054c8ae))
* **settings:** add schedule enable/disable toggle ([f509679](https://github.com/TobySuch/earlybird/commit/f50967927805d97955563995f7ba65937d6da6cd))
* **ui:** add episode permalink view at /episodes/{id} ([c7c5458](https://github.com/TobySuch/earlybird/commit/c7c54584aa5b4da706eb7c7a4480738ceb9ff9e2))
* **ui:** add latest episode link to dashboard episodes card ([6beaa53](https://github.com/TobySuch/earlybird/commit/6beaa5309074d7191c93ec491f3caa1f43f78031))
* **ui:** add podcast player to episodes list and fix Firefox range input ([a935510](https://github.com/TobySuch/earlybird/commit/a935510b4a41d6ee167c0156a8c144c2070cb9bd))
* **ui:** poll running status every 5s via HTMX partials ([87cff0e](https://github.com/TobySuch/earlybird/commit/87cff0e2bdb351598ac98d932b292994e9620aea))
* **ui:** replace dashboard stats with side-by-side cards ([8d2fa3d](https://github.com/TobySuch/earlybird/commit/8d2fa3d3282d576633292538c12c68fb09632f11))
* **ui:** replace dashboard stats with side-by-side cards ([29f287b](https://github.com/TobySuch/earlybird/commit/29f287b5e01e6789cd911b655f30524af47826b0))
* **ui:** wire up episodes and settings pages ([1796f2f](https://github.com/TobySuch/earlybird/commit/1796f2f618111830e6daabe0d095fd80c14d12aa))


### Bug Fixes

* **ci:** add token to checkout step for commitlint action ([cd10130](https://github.com/TobySuch/earlybird/commit/cd10130710eb8348c9fe4506d1cb23394b296aa0))
* **ci:** add token to checkout step for commitlint action ([46b604f](https://github.com/TobySuch/earlybird/commit/46b604f7c9f3bd479194be734c39480758bab476))
* **ci:** fix Dependabot PR failures — commitlint permissions and test DB ([8288ea0](https://github.com/TobySuch/earlybird/commit/8288ea07f3a3799103cc48e2b54181e15b9a0e01))
* **ci:** skip commitlint for Dependabot PRs ([36e9f45](https://github.com/TobySuch/earlybird/commit/36e9f45e43577c2f6f4ee02c7f256587e189de0f))
* **db:** handle empty alembic_version table and restore startup logging ([5f1d5e9](https://github.com/TobySuch/earlybird/commit/5f1d5e9643dd26371710d1e723e20abb9391e29f))
* **docker:** copy alembic.ini and migrations into image ([8ff0b01](https://github.com/TobySuch/earlybird/commit/8ff0b0146f58763be1862e7e818e4f802ff636d4))
* **pipeline:** skip empty newsletters and exit early when none found ([823f2bc](https://github.com/TobySuch/earlybird/commit/823f2bca1152df05cb8c7e2340a15c42921bb22a))
* **ui:** add cursor-pointer to all interactive elements ([2abd3e5](https://github.com/TobySuch/earlybird/commit/2abd3e5ad047ec7b0646a76e67fa8eb8803c36f0))
* **ui:** display newsletters_found in run log table ([62507a0](https://github.com/TobySuch/earlybird/commit/62507a047beb25722b50672332f3adc66d8c34af))
* **ui:** fix audio widget duration not loading ([e8a5fe3](https://github.com/TobySuch/earlybird/commit/e8a5fe38d0cb63dac7d5e5dde44b4df6ded0276f))
* **ui:** fix episode accordion collapse and improve timestamp ([51ed6fb](https://github.com/TobySuch/earlybird/commit/51ed6fb71663e04cf5536606529d8c46e4825ad6))


### Code Refactoring

* **auth:** adopt maddieverse pairing code style ([95c85fc](https://github.com/TobySuch/earlybird/commit/95c85fc049cdaf9e17af1e4ce0f2e877b6719aa6))
* **config:** migrate config.yml settings to DB and settings UI ([6514670](https://github.com/TobySuch/earlybird/commit/6514670c12bd793bf8eddd09268c93faa3c4839c))
* **ingest:** introduce pluggable source interface, rename Newsletter to NewsSource ([fe4cd93](https://github.com/TobySuch/earlybird/commit/fe4cd93976e9f97e88ccb735bd5ccdc560945f5d))
* **models:** remove Source, rename Story to Newsletter ([8227e53](https://github.com/TobySuch/earlybird/commit/8227e532d5a412b7cbc3deabf0dbb3396fdfa768))
* **ui:** extract audio widget into a shared Jinja2 macro ([4a358a6](https://github.com/TobySuch/earlybird/commit/4a358a68426c581c473af4842e434631479d05e6))
