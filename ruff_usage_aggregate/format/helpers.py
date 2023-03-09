def format_bar(value: float, max_value: float, width: int) -> str:
    w = width * value / max_value
    w_i, w_f = int(w), w - int(w)
    bar = "\u2588" * w_i
    if w_f > 0.75:
        bar += "\u258A"
    elif w_f > 0.5:
        bar += "\u258C"
    elif w_f > 0.25:
        bar += "\u258E"
    return bar.ljust(width, "\u2581")
