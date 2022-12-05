# Monoformat

Opinionated and "zero config" formatters like Black and Prettier are amazing in
the sense that they remove any need for thinking about formatting. However, they
still require you to:

-   Be used separately (one is Python and the other is Node)
-   Be configured for the language version and so forth

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

## Supported languages

Monoformat supports the following languages:

-   **Python** (Black)
-   **JavaScript** (Prettier)
-   **TypeScript** (Prettier)
-   **JSON** (Prettier)
-   **Markdown** (Prettier)
-   **YAML** (Prettier)
-   **HTML** (Prettier)
-   **CSS** (Prettier)
-   **SCSS** (Prettier)
-   **Vue** (Prettier)
-   **Svelte** (Prettier)
-   **PHP** (Prettier)
