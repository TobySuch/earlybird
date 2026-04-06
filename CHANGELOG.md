# Changelog

## [0.4.0](https://github.com/TobySuch/earlybird/compare/v0.3.0...v0.4.0) (2026-04-06)


### Features

* **auth:** add single-user authentication ([3d1fa03](https://github.com/TobySuch/earlybird/commit/3d1fa0330d94d2cc46ad223a1f872108f3e09321))
* **dashboard:** add Check inbox button to count unprocessed Gmail emails ([#11](https://github.com/TobySuch/earlybird/issues/11)) ([91d6f5a](https://github.com/TobySuch/earlybird/commit/91d6f5a2a9afb8dcb547bfd54ab034a661dd7074))
* **db:** add Alembic migrations ([91ff353](https://github.com/TobySuch/earlybird/commit/91ff3535baec3997d35fee7071e43ca75f32f511))
* **frontend:** upgrade Tailwind CSS v3 → v4 ([8d36f24](https://github.com/TobySuch/earlybird/commit/8d36f247d7f44c9ece1c3c7dc37aafeb72d3f48a))
* **ingest:** implement Gmail OAuth2 auth and email ingestion ([3ca2926](https://github.com/TobySuch/earlybird/commit/3ca2926d9cca39374c6fb23d3d56ee30ef6c38c3))
* **llm:** add OpenAI-compatible API provider ([945888b](https://github.com/TobySuch/earlybird/commit/945888bff1b6f6d0a163cf8ff19d1bf19c5e6b50))
* **llm:** add OpenRouter attribution headers to all LLM providers ([#10](https://github.com/TobySuch/earlybird/issues/10)) ([075a525](https://github.com/TobySuch/earlybird/commit/075a525c056dce27d433e3293b00c211b9ccc9a3))
* **pipeline:** implement ElevenLabs TTS podcast generation ([5a0b360](https://github.com/TobySuch/earlybird/commit/5a0b36062d2990fada6a28e55906704b5dae491f))
* **pipeline:** implement LLM summarisation with pluggable provider interface ([1d8db4c](https://github.com/TobySuch/earlybird/commit/1d8db4c7298efff0a60ef872eabfd1ff61bdc94d))
* **pipeline:** wire up run trigger, per-run logging, and run detail UI ([0c70a35](https://github.com/TobySuch/earlybird/commit/0c70a35c65801bbbd1a02268fa71098d0ee8a4e7))
* **project:** initial project scaffold ([bd96a36](https://github.com/TobySuch/earlybird/commit/bd96a366c4b9cb35664079657baaf8eaa054c8ae))
* **settings:** add schedule enable/disable toggle ([f509679](https://github.com/TobySuch/earlybird/commit/f50967927805d97955563995f7ba65937d6da6cd))
* **tts:** add pluggable TTS provider with OpenAI-compatible support ([3b26af4](https://github.com/TobySuch/earlybird/commit/3b26af4fa37c25cf1bb7ae3d71d7f8d537a2cdcf))
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
* **pipeline:** defer Gmail processed label until full pipeline succeeds ([4e17710](https://github.com/TobySuch/earlybird/commit/4e17710bede19186b28ac43fea2346a8d1c7add1))
* **pipeline:** skip empty newsletters and exit early when none found ([823f2bc](https://github.com/TobySuch/earlybird/commit/823f2bca1152df05cb8c7e2340a15c42921bb22a))
* **ui:** add cursor-pointer to all interactive elements ([2abd3e5](https://github.com/TobySuch/earlybird/commit/2abd3e5ad047ec7b0646a76e67fa8eb8803c36f0))
* **ui:** display newsletters_found in run log table ([62507a0](https://github.com/TobySuch/earlybird/commit/62507a047beb25722b50672332f3adc66d8c34af))
* **ui:** fix audio widget duration not loading ([e8a5fe3](https://github.com/TobySuch/earlybird/commit/e8a5fe38d0cb63dac7d5e5dde44b4df6ded0276f))
* **ui:** fix episode accordion collapse and improve timestamp ([51ed6fb](https://github.com/TobySuch/earlybird/commit/51ed6fb71663e04cf5536606529d8c46e4825ad6))

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
