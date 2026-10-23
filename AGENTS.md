# Personal repository identity and isolation

This is Calder's personal repository, not a Healthier business repository.

- Always use the GitHub account `caldermf` for all work associated with this repository, including commits, pushes, branches, pull requests, issues, and GitHub API operations.
- Never make changes, author commits, or perform GitHub operations as `cal-healthier` or any Healthier business identity.
- Before committing or performing authenticated GitHub operations, verify that the Git author/committer identity belongs to `caldermf` and that the active GitHub credentials authenticate as `caldermf`. If either identity is wrong or cannot be verified, stop the affected operation until it is corrected. Never fall back to `cal-healthier`.
- Use repository-local Git identity settings when configuration is needed; do not change global Git identity settings.
- Keep this repository completely separate from Healthier. Never copy, import, reference, or reuse Healthier code, data, documents, assets, secrets, credentials, configuration, or other business materials in this repository.
- Do not connect this repository to Healthier accounts, organizations, infrastructure, deployments, or services. Use only personal resources authorized for this repository.
- The local filesystem path or operating-system username does not authorize use of a Healthier identity. Work in this repository is performed as `caldermf`, never as `cal-healthier`.

## Local development

- `./bin/dev -d` builds and starts the Docker preview at http://localhost:8080.
- `./bin/build` builds the production site; `./bin/stop` stops the preview.
- Keep `Gemfile.lock` tracked. GitHub Actions deploys pushes to `main` or `master`.
- Preserve personal content, research notebooks, and the theme's `LICENSE` when cleaning up template files.
