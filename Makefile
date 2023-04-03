DEPENDNAME := dependents-$(shell date "+%Y%m%d-%H%M%S")
KNOWN_GITHUB_TOMLS := data/known-github-tomls.jsonl
DEP_NOT_FOUND := data/dep-not-found.jsonl

.PHONY: default scrape

default: out/results.md out/results.json

tomls: $(KNOWN_GITHUB_TOMLS)
	ruff-usage-aggregate download-tomls -o $@ < $<
	touch tomls

out/results.md: tomls
	ruff-usage-aggregate scan-tomls -i $< -o markdown > $@

out/results.json: tomls
	ruff-usage-aggregate scan-tomls -i $< -o json > $@

scrape-dependents:
	mkdir -p tmp
	python3 aux/scrape_dependents.py > tmp/$(DEPENDNAME)-scrape.txt
	python aux/guess_repo_name_to_jsonl.py --known-jsonl $(KNOWN_GITHUB_TOMLS) --known-json $(DEP_NOT_FOUND) < $(DEPENDNAME)-scrape.txt > tmp/$(DEPENDNAME)-out.jsonl
	ruff-usage-aggregate combine $(KNOWN_GITHUB_TOMLS) tmp/$(DEPENDNAME)-out.jsonl > tmp/$(DEPENDNAME)-combined.jsonl
	cp tmp/$(DEPENDNAME)-combined.jsonl $(KNOWN_GITHUB_TOMLS)
