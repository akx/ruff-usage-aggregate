import time

import tqdm


def sleep_with_progress(duration, description):
    """Sleep for a duration with a progress bar."""
    for _ in tqdm.tqdm(range(duration), unit="s", unit_scale=True, desc=description):
        time.sleep(1)
