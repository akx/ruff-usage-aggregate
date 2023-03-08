# ruff-usage-aggregate

Aggregate Ruff configuration data.

See https://github.com/charliermarsh/ruff/issues/3365.

## Usage

Do e.g. `pip install -e .` to install the package in a virtualenv.
Use the `[histogram]` extra to also get, well, histograms.

The tool will store its data in a `.cache` directory in the working directory in the DiskCache format.

The major workflow is:

1. Find files to scan.
   - `scan-github-search` (or other data sources, to be implemented) to find possible candidate TOML files.
     - To use this, you'll need to set the `GITHUB_TOKEN` environment variable to a GitHub API token. You can also
       place it in a file called `.env` in the working directory.
   - See the section below for how to get more URLs by hand, if/when that's not enough.
2. Download the files.
   - `download-tomls-from-cache` to download the TOML files found by the above scan
   - `download-tomls-from-file` to download TOML files from stdin (assumed to be GitHub URLs)
3. Aggregate data from downloaded files.
   - `scan-tomls -o json` will dump aggregate data to stdout in JSON format.
   - `scan-tomls -o top-markdown` will dump aggregate data to stdout in a pre-formatted Markdown format.

### Getting more URLs by hand

If the search API (`scan-github-search`) is not satisfactory, you can try and use the new GitHub Code Search
UI to find more URLs; these console scripts might help.

```javascript
var blobUrls = new Set();
// on each page
[...document.querySelectorAll("a[data-testid=link-to-search-result]")].forEach(
  (a) => blobUrls.add(new URL(a.href, location).href)
);
document.querySelector('a[aria-label="Next Page"]').click();
// copy results
copy([...blobUrls].sort().join("\n"));
```

## License

`ruff-usage-aggregate` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
