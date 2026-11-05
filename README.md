# pixi-app-template
Template for python application repos on pcdshub that use pixi to manage dependencies.

# Quickstart
- Create a new repo, selecting this repo as the template
- Complete the following checklist:

## TODO after starting a repo with this template:

- [ ] Update the primary group in CODEOWNERS to be a code owners team that you are a part of
- [ ] Review the pull request template: update, adapt, replace as needed
- [ ] Edit this README to be about your project, not about the template
- [ ] Find and replace pixi-app-template with your repo name
- [ ] Find and replace pixi_app_template with your import name
- [ ] Rename src/pixi_app_template to have your import name
- [ ] Check pixi.toml, pyproject.toml, docs/source/conf.py, and .github/workflows/pixi_test.yml carefully for leftover template artifacts

## Optional TODO
- [ ] Put something useful in the docs
- [ ] Set up a github-pages environment and enable the docs upload workflow
- [ ] Set up a pypi environment, configure pypi trusted publishing, and enable the pypi upload workflow

# Helpful Commands
- `pixi add`: add a package
- `pixi update`: update dependencies to latest versions that match our pins
- `pixi upgrade`: update version pins
- `pixi install`: set up the local pixi environment without running any specific command
- `pixi run test`: run the (pytest) unit tests
- `pixi run docs`: make the html docs
- `pixi run lint`: run all the linting (pre-commit) steps

# Tools and Norms
The following tools and norms are selected for this template:
- Use `pyproject.toml` for all python packaging configuration
- Use `pixi` to define the standard build/test/deploy environment for reproducible deployments
- Place the code in src and use `uv_build`
- Place tests in an installed tests submodule and use `pytest`
- Use `pre-commit` and `ruff` to define linting rules
- Define CI jobs for `GitHub Actions`, using the workflows in `pcds-ci-helpers`
- Use `sphinx` to build html docs

## Versions
The packages used here have aggressive version floors to encourage us to use the latest versions when possible.
If it is not possible to use the latest versions, feel free to roll them back.

Notable version pins to consider as optional include:
- python 3.14, which is still very new. This version was picked deliberately, but regressing to e.g. 3.12 would be acceptable.
- The versions of `uv_build`, `pytest`, and `sphinx` were picked with no consideration at all, just today's latest.

If you want to reduce these pins, the simplest way is to edit `pyproject.toml` and `pixi.toml` as appropriate.

## Other Choices
The template needs to take an opinionated stand on defaults, but you may consider alternatives for:
- build-system: this uses `uv_build` because it's really fast, but you could consider `hatchling` or `setuptools` if you prefer them.
- documentation: `sphinx` is used due to its proliferation in the python ecosystem but you could switch to e.g. `mkdocs` or something else.
- package management: you could abandon `pixi` for pure `uv`, but then you really ought to use a different template
