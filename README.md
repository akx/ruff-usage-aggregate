# ruff-usage-aggregate

Aggregate Ruff configuration data.

See https://github.com/charliermarsh/ruff/issues/3365.

## Usage

Do e.g. `pip install -e .` to install the package in a virtualenv.
Use the `[histogram]` extra to also get, well, histograms.

The major workflow is:

1. Find files to scan.
   - `ruff-usage-aggregate scan-github-search` (or other data sources, to be implemented) to find possible candidate TOML files.
     - To use this, you'll need to set the `RUA_GITHUB_TOKEN` environment variable to a GitHub API token. You can also
       place it in a file called `.env` in the working directory.
     - It will output a `github_search_*` JSONL file that can be parsed later.
   - There's also a `data/known-github-tomls.jsonl` file in the repository, which contains a list of known TOML files.
   - You can use the `ruff-usage-aggregate combine` command to combine github search files, CSV and JSONL files to a new `known-github-tomls.jsonl` file.
2. Download the files.
   - Run e.g. `ruff-usage-aggregate download-tomls -o tomls/ < data/known-github-tomls.jsonl` to download TOML files to the `tomls/` directory.
3. Aggregate data from downloaded files.
   - `ruff-usage-aggregate scan-tomls -i tomls -o json` will dump aggregate data to stdout in JSON format.
   - `ruff-usage-aggregate scan-tomls -i tomls -o top-markdown` will dump aggregate data to stdout in a pre-formatted Markdown format.

## License

`ruff-usage-aggregate` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
