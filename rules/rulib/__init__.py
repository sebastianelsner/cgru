import os
import sys
import traceback

CGRU_LOCATION = None
CGRU_VERSION = None

FILE_MAX_LENGTH = 3000000

HT_ACCESS_FILE_NAME = '.htaccess'
HT_GROUPS_FILE_NAME = '.htgroups'
HT_DIGEST_FILE_NAME = '.htdigest'

RUFOLDER = '.rules'
RECENT_FILENAME = 'recent.json'

RULES_TOP = dict()

ROOT = None

SKIPFILES = ['.', '..', HT_ACCESS_FILE_NAME, HT_GROUPS_FILE_NAME, HT_DIGEST_FILE_NAME]

GUESTCANCREATE = ['status.json', 'comments.json']
GUESTCANEDIT = ['comments.json']


from . import editobj
from . import functions
from . import news
from . import search
from . import status


if len(RULES_TOP) == 0:
    CGRU_LOCATION = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    CGRU_VERSION = functions.fileRead(os.path.join(CGRU_LOCATION,'version.txt'))

    os.environ['CGRU_LOCATION'] = CGRU_LOCATION
    os.environ['CGRU_VERSION'] = CGRU_VERSION
    os.environ['AF_ROOT'] = os.path.join(CGRU_LOCATION, 'afanasy')

    sys.path.append(os.path.join(CGRU_LOCATION, 'lib', 'python'))
    sys.path.append(os.path.join(CGRU_LOCATION, 'afanasy', 'python'))

    RULES_TOP = functions.getRulesUno(CGRU_LOCATION,'rules')

    if 'root' in RULES_TOP:
        try:
            ROOT = os.readlink(os.path.join(CGRU_LOCATION, RULES_TOP['root']))
        except:
            print('%s' % traceback.format_exc())
            ROOT = os.path.join(CGRU_LOCATION, RULES_TOP['root'])


def setTask(path=None, uid=None, name=None, tags=None, artists=None, flags=None, progress=None, annotation=None, deleted=None, nonews=False, out=None):
    if out is None:
        out = dict()

    st = status.Status(uid, path)

    st.setTask(tags=tags, artists=artists, flags=flags, progress=progress, annotation=annotation, deleted=deleted, out=out)

    if 'error' in out:
        return out

    # News & Bookmarks:
    # At first we should emit news,
    # as some temporary could be added for news.
    # For example task.changed = true
    news.statusChanged(st, out, nonews)

    st.save(out)

    if st.progress_changed:
        progresses = dict()
        progresses[st.path] = st.data['progress']
        status.updateUpperProgresses(os.path.dirname(st.path), progresses, out)

    return out
