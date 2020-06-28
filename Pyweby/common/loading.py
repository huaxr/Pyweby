import sys
import time


def loading(t):
    for _ in range(t):
        for i in ["[ - ]","[ \ ]","[ | ]","[ / ]"]:
            sys.stdout.write("\r" + "%s Server launching..." %i )
            time.sleep(0.2)
            sys.stdout.flush()
        sys.stdout.write('\r')
    sys.stdout.write('\r')