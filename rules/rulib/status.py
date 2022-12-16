import json
import os
import traceback

import rulib

def getStatusFilePath(i_path = None):
    return rulib.functions.getRuFilePath('status.json', i_path)

def getStatusData(i_path = None, out = None):
    data = rulib.functions.readObj(getStatusFilePath(i_path), out)
    if data is None:
        return None
    if 'status' in data:
        return data['status']
    error = 'Status data not found'
    if out is not None: out['error'] = error
    else: print(error)
    return  None

def saveStatusData(i_path, i_data, out=None):
    path = getStatusFilePath(i_path)
    rufolder = os.path.dirname(path)
    if not os.path.isdir(rufolder):
        try:
            os.makedirs(rufolder)
        except PermissionError:
            err = 'Permissions denied to make folder for status: ' + rufolder
            if out is not None: out['error'] = err
            else: print(err)
            return
        except:
            err = 'Unable to create folder for status: ' + rufolder
            err += '\n%s' % traceback.format_exc()
            if out is not None: out['error'] = err
            else: print(err)
            return
    rulib.functions.writeObj(path, {'status':i_data}, out)

class Status:

    def __init__(self, uid=None, path=None):

        self.path = rulib.functions.getRootPath(path)

        self.muser = uid
        if self.muser is None:
            self.muser = rulib.functions.getCurUser()
        self.mtime = rulib.functions.getCurSeconds()

        self.data = getStatusData(self.path)
        if self.data is None:
            self.data = dict()

        self.progress_changed = False

    def __repr__(self):
        return json.dumps(self.data)

    def __str__(self):
        return json.dumps({"status":self.data})

    def findTask(self, name=None, tags=None, out=None):
        if 'tasks' not in self.data:
            return None
        if len(self.data['tasks']) == 0:
            return None
        if name is not None:
            if name in self.data['tasks']:
                return self.data['tasks'][name]
            return None

        if tags is None or not type(tags) is list or len(tags) == 0:
            error = 'No task name or tags list specified.'
            if out is None: print(error)
            else: out['error'] = error
            return None

        for task in self.data['tasks']:
            task = self.data['tasks'][task]
            if len(tags) != len(task['tags']):
                continue
            for tag in tags:
                if not tag in task['tags']:
                    task = None
                    break
            if task is not None:
                return task

        return None


    def setTask(self, name=None, tags=None, artists=None, flags=None, progress=None, annotation=None, deleted=None, out=None):

        task = self.findTask(name, tags)

        if task is None:
            # Create a new task:
            task = dict()
            if tags is None or not type(tags) is list or len(tags) == 0:
                error = 'No new task tags list specified.'
                if out is None: print(error)
                else: out['error'] = error
                return None
            if name is None:
                if tags is None or len(tags) == 0:
                    error = 'Task should have name or tags.'
                    if out is None: print(error)
                    else: out['error'] = error
                    return None
                tags.sort()
                name = '_'.join(tags)
            task['name'] = name
            task['tags'] = tags
            task['artists'] = []
            task['flags'] = []
            task['progress'] = 0
            task['cuser'] = self.muser
            task['ctime'] = self.mtime

            if not 'tasks' in self.data:
                self.data['tasks'] = dict()
            self.data['tasks'][name] = task

        else:
            task['muser'] = self.muser
            task['mtime'] = self.mtime

        if artists is not None and type(artists) is list:
            task['artists'] = artists
        if flags is not None and type(flags) is list:
            task['flags'] = flags
        if annotation is not None and type(annotation) is str:
            task['annotation'] = annotation
        if deleted is not None:
            task['deleted'] = deleted

        if progress is not None and type(progress) is int:
            if progress < -1: progress = -1
            elif progress > 100: progress = 100
        elif 'progress' in task:
            progress = task['progress']
        else:
            progress = 0

        # Task flags can detemine task progress (eg done=100%)
        if flags is not None and len(flags):
            for flag in flags:
                if not flag in rulib.RULES_TOP['flags']:
                    continue
                p_min = None
                p_max = None
                if 'p_min' in rulib.RULES_TOP['flags'][flag]:
                    p_min = rulib.RULES_TOP['flags'][flag]['p_min']
                if 'p_max' in rulib.RULES_TOP['flags'][flag]:
                    p_max = rulib.RULES_TOP['flags'][flag]['p_max']
                if p_min is not None and progress < p_min: progress = p_min
                if p_max is not None and progress > p_max: progress = p_max

        # Set task progress if it changes:
        if not 'progress' in task or task['progress'] != progress:
            task['progress'] = progress

            # Calculate status progress - tasks progress average
            avg_progress = 0.0
            num_tasks = 0

            for t in self.data['tasks']:
                _task = self.data['tasks'][t]
                if 'deleted' in _task and _task['deleted']:
                    continue

                koeff = 1.0
                if t in rulib.RULES_TOP['tags'] and 'koeff' in rulib.RULES_TOP['tags'][t]:
                    koeff = rulib.RULES_TOP['tags'][t]['koeff']

                avg_progress += koeff * _task['progress']
                num_tasks += koeff

            # Set status progress if it changes:
            avg_progress = round(avg_progress / num_tasks)
            if 'progress' not in self.data or self.data['progress'] != avg_progress:
                self.data['progress'] = avg_progress
                self.progress_changed = True
            else:
                self.progress_changed = False


        # Remove status tags, artists and flags if the task has the same
        for arr in ['tags','artists','flags']:
            if arr in self.data and len(self.data[arr]):
                for item in task[arr]:
                    if item in self.data[arr]:
                        self.data[arr].remove(item)

        # Set task changed.
        # It needed for news to know what was changed in status.
        task['changed'] = True

        return task


    def prepareDataForSave(self):
        if 'changed' in self.data:
            del self.data['changed']
        if 'tasks' in self.data:
            for t in self.data['tasks']:
                if 'changed' in self.data['tasks'][t]:
                    del self.data['tasks'][t]['changed']


    def save(self, out=dict(), nonews=False):
        self.data['mtime'] = self.mtime
        self.data['muser'] = self.muser

        rulib.news.statusChanged(self, out, nonews)

        self.prepareDataForSave()

        saveStatusData(self.path, self.data, out)

        out['status'] = self.data

        if self.progress_changed:
            progresses = dict()
            progresses[self.path] = self.data['progress']
            updateUpperProgresses(os.path.dirname(self.path), progresses, out)


def updateUpperProgresses(i_path, i_progresses, out):
    #print(i_path)
    path = ''
    folders = []
    for folder in i_path.split('/'):
        if len(folder) == 0: continue
        path += '/' + folder
        folders.append(path)

    out['progresses'] = dict()

    folders.reverse()
    for folder in folders:
        #print(folder)
        try:
            listdir = os.listdir(rulib.functions.getAbsPath(folder))
        except:
            return

        progress_sum = 0
        progress_count = 0
        for entry in listdir:
            if entry == rulib.RUFOLDER:
                continue

            progress = 0
            path = os.path.join(folder, entry)
            if path in i_progresses:
                progress = i_progresses[path]
            else:
                sdata = getStatusData(path)
                if sdata and 'progress' in sdata:
                    progress = sdata['progress']

            #print(entry, progress)

            if progress < 0:
                continue

            progress_sum += progress
            progress_count += 1

        if progress_count == 0:
            return

        progress_avg = int(progress_sum / progress_count)
        i_progresses[folder] = progress_avg

        #print("%s %d%%" % (folder, progress_avg))

        sdata = getStatusData(folder)
        if sdata is None:
            sdata = {'progress':progress_avg}
        else:
            sdata['progress'] = progress_avg
        saveStatusData(folder, sdata)

        out['progresses'][folder] = progress_avg
