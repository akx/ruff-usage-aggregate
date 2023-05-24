TS := $(shell date "+%Y%m%d-%H%M%S")
KNOWN_GITHUB_TOMLS := data/known-github-tomls.jsonl
KNOWN_GITHUB_TOMLS_CLEAN := data/known-github-tomls-clean.jsonl
REPO_API_DATA := data/repo_api_data.jsonl
DEP_NOT_FOUND := data/path-unknown.jsonl

.PHONY: default scrape scrape-search scrape-dependents

default: out/results.md out/results.json

tomls: $(KNOWN_GITHUB_TOMLS)
	ruff-usage-aggregate download-tomls -o $@ < $<
	touch tomls

out/results.md: tomls
	ruff-usage-aggregate scan-tomls -i $< -o markdown > $@

out/results.json: tomls
	ruff-usage-aggregate scan-tomls -i $< -o json > $@

scrape: scrape-search scrape-dependents

scrape-search:
	mkdir -p tmp
	ruff-usage-aggregate scan-github-search -o tmp/$(TS)-search.jsonl
	ruff-usage-aggregate combine $(KNOWN_GITHUB_TOMLS) tmp/$(TS)-search.jsonl > tmp/$(TS)-combined.jsonl
	cp tmp/$(TS)-combined.jsonl $(KNOWN_GITHUB_TOMLS)

scrape-dependents:
	mkdir -p tmp
	python3 aux/scrape_dependents.py > tmp/$(TS)-scrape.txt
	python aux/guess_repo_name_to_jsonl.py --known-jsonl $(KNOWN_GITHUB_TOMLS) --known-json $(DEP_NOT_FOUND) < tmp/$(TS)-scrape.txt > tmp/$(TS)-out.jsonl
	ruff-usage-aggregate combine $(KNOWN_GITHUB_TOMLS) tmp/$(TS)-out.jsonl > tmp/$(TS)-combined.jsonl
	cp tmp/$(TS)-combined.jsonl $(KNOWN_GITHUB_TOMLS)

clean-with-repo-api:
	ruff-usage-aggregate clean-with-repo-api $(KNOWN_GITHUB_TOMLS) $(KNOWN_GITHUB_TOMLS_CLEAN) $(REPO_API_DATA)

gist:
	cat out/results.md | gh gist create --public -d "ruff-usage-aggregate $(shell date +%Y-%m-%d)" -f results.md
