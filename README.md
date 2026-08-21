# Monoformat

Opinionated and "zero config" formatters like Ruff and Prettier are amazing in
the sense that they remove any need for thinking about formatting. However, they
still require you to:

- Be used separately (one is Python and the other is Node)
- Be configured for the language version and so forth

Monoformat does this automatically. You can only use the language version that
monoformat allows and you can configure literally nothing except which files
it's going to reformat and which it's not.

## Installation

Monoformat is available on PyPI:

```bash
pip install monoformat
```

## Usage

Monoformat is a command line tool. You can run it with:

```bash
monoformat .
```

This will reformat all files in the current directory and its subdirectories.

It will take care to avoid `.git` and other special directories. There is a
default pattern embedded but you can change it with the `--do-not-enter` flag,
which is a pattern matching folder or file names you don't want to consider.

On addition to the `--do-not-enter` rule, it will by default check all
`.gitignore` files and `.formatignore` files (which use the `.gitignore` syntax
but only affect the decision of whether to format a file or not, not to put them
in git) and.

### Default project

Let's say you have a Django project. It contains lots of files, including a
`node_modules` somewhere and a _a lot_ of big migration files.

You might want to have at the root of your repo a `.gitignore` file that looks
like that:

```
node_modules
.idea
.vscode
.env
*.pyc
```

And then specifically to avoid formatting migrations (which can be super
expensive), and to avoid running prettier on Django templates (which ends up
badly) add a `.formatignore` file that looks like that:

```
**/migrations/*
**/templates/*
```

Then you can run `monoformat .` and it will only format the files that are
relevant to your project.

### Without install

I've actually spent an absurd amount of time to make it extremely simple to run
Python and JS code without installing anything. You can do this with:

```bash
curl -s https://pypi.run/monoformat | python3 - .
```

Doing so will entirely reformat with Ruff, oxfmt and Prettier the current
directory.

## Supported languages

Monoformat supports the following languages:

- **Python** (Ruff, both import sorting and Black-style formatting)
- **JavaScript** (oxfmt)
- **TypeScript** (oxfmt)
- **JSON** (Prettier)
- **Markdown** (Prettier)
- **YAML** (Prettier)
- **HTML** (Prettier)
- **CSS** (Prettier)
- **SCSS** (Prettier)
- **Less** (Prettier)
- **Vue** (Prettier)
- **Svelte** (Prettier)
- **MJML** (Prettier)
- **PHP** (Prettier)

JavaScript and TypeScript run through [oxfmt](https://oxc.rs), which is
Prettier-compatible in style but dramatically faster. Everything that runs
through Prettier or oxfmt requires Node to be available. If you don't have a
system-wide Node installation, you can get one bundled as a Python wheel:

```bash
pip install monoformat[node]
```
