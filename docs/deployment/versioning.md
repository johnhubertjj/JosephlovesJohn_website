# Versioning

This project uses lightweight semantic versioning with git releases:

- `v1.0.0` = first public live release
- `v1.0.1` = next patch release after launch
- patch (`x.y.Z`) = bug fixes, launch polish, operational fixes
- minor (`x.Y.z`) = new features that do not break existing flows
- major (`X.y.z`) = large or breaking structural changes

## Release Rule

- keep the current production release tagged in git
- treat the working tree as the next unreleased version
- update [CHANGELOG.md](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/CHANGELOG.md) when a release-worthy change lands
- create the git tag only when that version is actually deployed

## Current State

- latest tagged release: `v1.1.1`
- current untagged working tree: `v1.2.0`

## Suggested Workflow

1. Merge release-ready work into `main`.
2. Update the changelog entry for the version being shipped.
3. Deploy on Render.
4. Smoke test production.
5. Tag the deployed commit, for example `v1.2.0`.
6. Start the next unreleased changelog section.
