.PHONY: default

default: out/results.md out/results.json

tomls: data/known-github-tomls.jsonl
	ruff-usage-aggregate download-tomls -o $@ < $<
	touch tomls

out/results.md: tomls
	ruff-usage-aggregate scan-tomls -i $< -o markdown > $@

out/results.json: tomls
	ruff-usage-aggregate scan-tomls -i $< -o json > $@
