# [1.2.0](https://github.com/olcortesb/s3rv3rl3ss-backend/compare/v1.1.1...v1.2.0) (2026-09-01)


### Features

* add ReinventFunction with date-based schedule and CloudFront invalidation ([81a8306](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/81a8306936f067187317ec17c3d990a096bef9df))
* invoke ReinventFunction daily from CollectorFunction with force=true ([b730eff](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/b730eff9117a9e83f7fb1c512283077b5b0ef72b))

## [1.1.1](https://github.com/olcortesb/s3rv3rl3ss-backend/compare/v1.1.0...v1.1.1) (2026-08-31)


### Bug Fixes

* CloudFront auto-invalidation for all collectors + exclude CommitterFunction from metrics ([a1a9a27](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/a1a9a27c92af6b760e142fae3ac6043d8a020124))

# [1.1.0](https://github.com/olcortesb/s3rv3rl3ss-backend/compare/v1.0.1...v1.1.0) (2026-08-31)


### Features

* CloudFront auto-invalidation + AWS Organizations + Control Tower ([7fb65fe](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/7fb65fe8731af649fa2867e2d014a112d1942c41))

## [1.0.1](https://github.com/olcortesb/s3rv3rl3ss-backend/compare/v1.0.0...v1.0.1) (2026-08-14)


### Bug Fixes

* remove hardcoded account ID from IAM policy ([b2657ba](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/b2657ba98031b84aca44432a339772631dc6f5a0))

# 1.0.0 (2026-08-14)


### Bug Fixes

* add parser to healt services ([7c09a53](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/7c09a53d5bf1cce38e2f507077e5f51c59b399ea))
* filter What's New by title only, blog feeds by title+description ([ec0c998](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/ec0c99882965eb3f8726b143188bb678e8f8c0a4))
* remove unused FUNCTIONS list, update secrets manager cost to 3 secrets ([e732570](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/e732570c741ff5e54cd831a6929d45f135ae9736))
* robotocore imagen name and docker login via secret manager ([8e6d809](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/8e6d809cc74b7f2e5955d02c3ab407d3064d47e4))
* use article publication date in changelog, expand news sources and keywords ([37c13f9](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/37c13f9105c8213f80fdebf01fc31c125bd79e2e))


### Features

* add automatically runtime update ([74a2efa](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/74a2efa83221053c42ecddaa84cd221a29156200))
* add aws rekognition ([23c419c](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/23c419c752cf77c6f37650c17d560d3d6ff553d0))
* add azure and x86 processor ([e6e0626](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/e6e0626a5baa406757d41ddf313c995dd5a1c3e1))
* add codebuild for docker validation ([6596c8c](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/6596c8c37cf5a34220f14bce7439c2a15c576b7b))
* add comparision lambda ([a81a1e9](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/a81a1e90691ffa80ae10efa61c76b768a7009e1e))
* add complete flow get and commit ([abe57df](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/abe57dfb1c81c26c206dc2848b6a21e8cdda6ecc))
* add dynamodb and lambda metrics ([250c39a](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/250c39a237701b03ffddd0e2231d0bb339da3992))
* add first version of stackit ([d7fde6b](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/d7fde6b53120c527cf415b0026fb8c08081359ab))
* add more services all providers ([bcdd80b](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/bcdd80b166b829df12b9288516997009750a9dae))
* add region to output + merge news with previous data ([b2cde20](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/b2cde2013f47cbaf4ca3cca38569d7da6f5d9732))
* add semantic release ([06f0422](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/06f0422f78bf48a06c62633c2da76f8bf7986cfd))
* add tools collector ([dc9554e](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/dc9554e7c57f28c96550636145554d34d4c8ec48))
* expand news sources - AWS keywords+description, GCP general feed fallback, Azure Updates feed ([6c1b118](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/6c1b118acffe3366893c5a7f9b93ff809e195894))
* extend changelog windows from 90 to 180 ([7d5f993](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/7d5f993514e60d8c71acd83406890c0e887616e4))
* improve google rss ([a6ff29d](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/a6ff29dc31c1f40eb9e53c2a441481b85d871eee))
* improve the tools-collector handler ([9506d90](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/9506d90a1e017dd7e3aade41186c9455d871d212))
* remove git layer and migrate commiter to github api commit ([8dfad8e](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/8dfad8e894b65accc7937b853461f1d550ff5db3))
* remove README/docs scraping, use only health endpoint data ([71edcc7](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/71edcc76f740ce0ee7e7b9a0cef7432c03767ac5))
* robotocore fix, docker login, localstack auth, service normalization and native/moto breakdown ([9294655](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/9294655966221b659b79eb4fb83f66704ac9303b))
* update backend services ([98d06c1](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/98d06c18901e2d7e32dee8f241f61debbff4a8fa))
* update fecth news ([fcbfa93](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/fcbfa930fca4078e8bfa54141d76874c7c010f66))
* update readme ([374dfb5](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/374dfb51a598629ed8de1da2b4665ade45479171))
* update readme and template.yaml ([b86034c](https://github.com/olcortesb/s3rv3rl3ss-backend/commit/b86034c29cf37c7cbda919dc3469431c8b82ec28))
