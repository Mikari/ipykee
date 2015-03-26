import IPython
import pickle
import os
import json
import urllib2
import shutil
from IPython.lib import kernel
import tempfile
import subprocess
import yaml
import settings
import datetime
from logging import debug, warn

from nbdiff.notebook_diff import notebook_diff
from nbdiff.server.local_server import app
import IPython.nbformat.current as current
import threading

config = settings.Settings()


class ProjectAlreadyExistException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class CalledCommandError(Exception):
    def __init__(self, cmd, retcode, out, err):
        self.cmd = cmd
        self.retcode = retcode
        self.out = out
        self.err = err

    def __str__(self):
        return "\n".join([
            "cmd: " + repr(self.cmd),
            "retcode: " + repr(self.retcode),
            "out: " + repr(self.out),
            "-----",
            "err: " + repr(self.err)])


def keep_cwd(func):
    def keep_cwd_and_call(*args, **kwargs):
        current_dir = os.getcwd()
        result = func(*args, **kwargs)
        os.chdir(current_dir)
        return result
    return keep_cwd_and_call


@keep_cwd
def delete_project(project_name):
    os.remove(os.path.join(config['project-dir'], project_name + ".yaml"))
    shutil.rmtree(
        os.path.join(config['project-dir'], project_name),
        ignore_errors=True
    )
    debug("Deleted project %s" % (project_name))


@keep_cwd
def create_project(project_name, repository=None, internal_path="."):
    config_file = os.path.join(config['project-dir'], project_name + ".yaml")
    if not os.path.exists(config_file):
        if not repository:
            debug("Creating local repository")
            repository = os.path.join(config['project-dir'], project_name)
            if not os.path.exists(repository):
                os.makedirs(repository)
            os.chdir(repository)
            execute_command("git init --bare", shell=True)

            tmp_dir = tempfile.mkdtemp()
            os.chdir(tmp_dir)
            execute_command(['git', 'clone', repository, project_name])
            os.chdir(os.path.join(tmp_dir, project_name))
            execute_command('git config user.name "ipykee"', shell=True)
            execute_command('git config user.email "ipykee@fake.email"', shell=True)
            execute_command('git commit --allow-empty -m "Created repository"', shell=True)
            execute_command("git push origin master", shell=True)
            remote = False
            # shutil.rmtree(tmp_dir)
        else:
            remote = True

        project_config = {
            "repository": repository,
            "name": project_name,
            "create-time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "internal-path": internal_path,
            "remote": remote
        }
        with open(config_file, "w") as out:
            yaml.dump(project_config, out)

        debug("Project %s has been created" % (project_name))
    else:
        raise ProjectAlreadyExistException("Project name: %s" % (project_name))

    if get_project_config(project_name)["remote"]:
        with open(config_file, "r") as in_stream:
            project_config = yaml.load(in_stream)
            keyfile = get_project_ssh_key_file(project_name)[:-4]

            if not os.path.exists(keyfile):
                execute_command(["ssh-keygen", "-t", "rsa", "-N", "", "-f", keyfile])
            print "Please don't forget to add this ssh key:\n" + get_project_ssh_key(project_name)


def dump_history(name, destination):
    console = IPython.get_ipython()
    with open(os.path.join(destination, "history_manual.py"), "w") as stream_out:
        stream_out.write("# -*- coding: utf-8 -*-\n")
        for ceil in console.history_manager.get_range():
            stream_out.write("\n\n# <codecell>\n\n" + ceil[2])

    shutil.copy(
        os.path.join(IPython.get_ipython().starting_dir, get_current_notebook_name() + ".ipynb"),
        os.path.join(destination, "notebook.ipynb")
    )
    console.run_cell("%notebook -e " + os.path.join(destination, "history.py"), silent=True)
    console.run_cell("%notebook -e " + os.path.join(destination, "history.ipynb"), silent=True)
    debug("Copied last saved state of notebook and dumped kernel history")


def dump_variables(name, variables, destination):
    with open(os.path.join(destination, "variables.dump"), 'w') as out:
        pickle.dump(variables, out)


def get_current_notebook_name():
    # http://stackoverflow.com/questions/12544056/how-to-i-get-the-current-ipython-notebook-name
    connection_file_path = kernel.get_connection_file()
    connection_file = os.path.basename(connection_file_path)
    kernel_id = connection_file.split('-', 1)[1].split('.')[0]

    # Updated answer with semi-solutions for both IPython 2.x and IPython < 2.x
    if IPython.version_info[0] < 2:
        ## Not sure if it's even possible to get the port for the
        ## notebook app; so just using the default...
        notebooks = json.load(urllib2.urlopen('http://' + config['ipython-url'] + 'notebooks'))
        for nb in notebooks:
            if nb['kernel_id'] == kernel_id:
                return nb['name']
    else:
        sessions = json.load(urllib2.urlopen('http://' + config['ipython-url'] + '/api/sessions'))
        for sess in sessions:
            if sess['kernel']['id'] == kernel_id:
                name = sess['notebook']['name']
                if name[-6:] == '.ipynb':
                    return name[:-6]
                else:
                    return name


def list_projects():
    projects = []
    for obj in os.listdir(config['project-dir']):
        if obj[-5:] == '.yaml':
            projects.append(obj[:-5])
    return projects


def get_project_config(project_name):
    path_config = os.path.join(config['project-dir'], project_name + ".yaml")
    try:
        with open(path_config) as stream_in:
            project_config = yaml.load(stream_in)
        return project_config
    except:
        raise ValueError("Project doesn't exist")


def get_git_env(project_config):
    env = os.environ.copy()
    if project_config['remote']:
        env["GIT_SSH"] = "ipykee-ssh-wrapper.sh"
        env["PKEY"] = get_project_ssh_key_file(project_config['name'])[:-4]
    return env


def get_project_ssh_key_file(project_name):
    return os.path.join(config["project-dir"], "id_rsa.ipykee." + project_name + ".pub")


def get_project_ssh_key(project_name):
    keyfile_path = get_project_ssh_key_file(project_name)
    key = ""
    with open(keyfile_path, "r") as keyfile:
        key = keyfile.read()
    return key


def execute_command(cmd, **kwargs):
    task = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    out, err = task.communicate()
    if task.returncode != 0:
        raise CalledCommandError(cmd, task.returncode, out, err)
    return (out, err)


class Keeper(object):
    def __init__(self, project_name):
        self.project_name = project_name
        self.ready = False
        self.work_dir = None
        self.project_config = get_project_config(project_name)
        self.env = get_git_env(self.project_config)

    @keep_cwd
    def _checkout(self, revision="HEAD"):
        if not self.work_dir:
            self.work_dir = tempfile.mkdtemp(dir=config["work-dir"])

        if not self.ready:
            os.chdir(self.work_dir)
            execute_command(['git', 'clone', self.project_config['repository'], self.project_name], env=self.env)
            os.chdir(os.path.join(self.work_dir, self.project_name))
            execute_command('git config user.name "ipykee"', shell=True)
            execute_command('git config user.email "ipykee@fake.email"', shell=True)
            execute_command('git config filter.media.clean "git-media filter-clean"', shell=True)
            execute_command('git config filter.media.smudge "git-media filter-smudge"', shell=True)
            execute_command('echo "*.dump filter=media -crlf" > .gitattributes', shell=True)
            execute_command('git config git-media.transport local', shell=True)
            execute_command(["git", "config", "git-media.localpath", config["git-media-path"]])
            execute_command("git media sync", shell=True)
            self.ready = True
        else:
            os.chdir(os.path.join(self.work_dir, self.project_name))
            try:
                # TODO: why it sometimes returns retcode=1?
                execute_command('git update-index --really-refresh', shell=True)
            except:
                pass
            execute_command("git checkout -f master", shell=True)
            execute_command(["git", "pull"], env=self.env)

            os.chdir(os.path.join(self.work_dir, self.project_name))
            execute_command("git checkout -f %s" % (revision), shell=True)
            execute_command("git media sync", shell=True)

    def list_notebooks(self):
        self._checkout()
        try:
            notebooks = os.listdir(os.path.join(self.work_dir, self.project_name, self.project_config['internal-path']))
        except OSError:
            notebooks = []
        ignored_files = [".git", ".gitattributes"]
        for ignored in ignored_files:
            try:
                notebooks.remove(ignored)
            except:
                pass
        return notebooks

    @keep_cwd
    def history(self, count=None, notebook=None):
        self._checkout()
        os.chdir(os.path.join(self.work_dir, self.project_name))
        cmd = "git log --pretty=oneline"
        if notebook:
            cmd += " | grep " + notebook
        if count:
            cmd += " | head -n " + str(count)
        history, _ = execute_command(cmd, shell=True)
        return [tuple(a.split(" ", 1)) for a in history.split("\n") if a]

    def cleanup(self):
        shutil.rmtree(self.work_dir)
        self.work_dir = None
        self.ready = False

    def __getitem__(self, notebook):
        return Session(notebook, self)

    def _get_variables(self, notebook, revision="HEAD"):
        self._checkout(revision)
        path_to_var_dump = os.path.join(
            self.work_dir,
            self.project_name,
            self.project_config['internal-path'],
            notebook,
            "variables.dump")

        if (os.path.exists(path_to_var_dump)):
            with open(path_to_var_dump, "r") as stream_in:
                objects = pickle.load(stream_in)
            return objects
        else:
            raise ValueError("Wrong revision or notebook name - variables.dump doesn't exist")

    @keep_cwd
    def _commit(self, notebook, message, variables={}):
        self._checkout()
        notebook_dir = os.path.join(self.work_dir, self.project_name, self.project_config['internal-path'], notebook)
        if not os.path.isdir(notebook_dir):
            os.makedirs(notebook_dir)
            debug("Created directory for notebook: %s" % (notebook))
        dump_history(notebook, notebook_dir)
        dump_variables(notebook, variables, notebook_dir)
        os.chdir(os.path.join(self.work_dir, self.project_name))
        try:
            # TODO: why it sometimes returns retcode=1?
            execute_command('git update-index --really-refresh', shell=True)
        except:
            pass
        execute_command(["git", "add", os.path.join(self.project_config['internal-path'], notebook, '*')])
        execute_command('git commit -a -m "' + notebook + ': ' + message + '"', shell=True)
        execute_command('git media clear', shell=True)
        execute_command(["git", "push", "origin", "master"], env=get_git_env(self.project_config))
        execute_command('git media sync', shell=True)
        debug("Successfuly commited")


class Session(object):
    def __init__(self, notebook=None, keeper=None, project_name=None):
        if not notebook:
            notebook = get_current_notebook_name()
            print "This notebook has name %s" % (notebook)
        self.notebook = notebook
        if not (keeper or project_name):
            raise ValueError("Please, define keeper or project_name")
        if not keeper:
            keeper = Keeper(project_name)
        self.keeper = keeper
        self.variables = dict()

        print "Please, save your notebook before commit!"

    def history(self, count=None):
        return self.keeper.history(count, self.notebook)

    def get_variables(self, revision="HEAD"):
        return self.keeper._get_variables(self.notebook, revision)

    def add(self, value, key):
        self.variables[key] = value

    def show_added(self):
        return self.variables.keys()

    def commit(self, message):
        self.keeper._commit(self.notebook, message, variables=self.variables)
        self.variables = dict()
        return self.history(count=1)[0]

    def get_file_types(self, revision="HEAD"):
        self.keeper._checkout(revision)
        result = []
        for obj in os.listdir(
            os.path.join(
                self.keeper.work_dir,
                self.keeper.project_name,
                self.keeper.project_config['internal-path'],
                self.notebook)):
            if obj[-6:] == '.ipynb':
                result.append(obj)
        return result

    def get_code(self, revision="HEAD", original_name=False, file_type="notebook"):
        self.keeper._checkout(revision)
        src = os.path.join(
            self.keeper.work_dir,
            self.keeper.project_name,
            self.keeper.project_config['internal-path'],
            self.notebook,
            file_type + ".ipynb")
        if original_name:
            dst_file = self.notebook + ".ipynb"
        else:
            dst_file = self.notebook + "@" + file_type + "@" + revision + ".ipynb"
        dst = os.path.join(IPython.get_ipython().starting_dir, dst_file)
        shutil.copy(src, dst)
        os.chdir(IPython.get_ipython().starting_dir)
        IPython.display.display(IPython.display.FileLink(dst_file))

    def diff_code(self, revision1, revision2):
        self.keeper._checkout(revision1)

        nb1 = current.reads(
            open(
                os.path.join(
                    self.keeper.work_dir,
                    self.keeper.project_name,
                    self.keeper.project_config['internal-path'],
                    self.notebook,
                    "notebook" + ".ipynb"),
                "r").read(),
            "ipynb")

        self.keeper._checkout(revision2)
        nb2 = current.reads(
            open(
                os.path.join(
                    self.keeper.work_dir,
                    self.keeper.project_name,
                    self.keeper.project_config['internal-path'],
                    self.notebook,
                    "notebook" + ".ipynb"),
                "r").read(),
            "ipynb")

        result_nb = notebook_diff(nb1, nb2)
        filename_placeholder = "{}-{}: {} and {}".format(
            self.keeper.project_name, self.notebook, revision1, revision2)
        app.add_notebook(result_nb, filename_placeholder)
        print "This diff have number {}".format(len(app.notebooks) - 1)

threads = {}


def start_diff_server(port=5000):
    print "Please, open hostname:{}/x (remember about docker), where x from 0 to {}".format(
        port, len(app.notebooks) - 1)
    if (port not in threads):
        threads[port] = threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "debug": False, "port": port})
        threads[port].start()
