// leave at least 2 line with only a star on it below, or doc generation fails
/**
*
*
* Ipykee button
*/


    IPython.toolbar.add_buttons_group([
    {
        'label'   : 'ipykee: create_session',
        'icon'    : 'fa-plus', // select your icon from http://fortawesome.github.io/Font-Awesome/icons
        'callback': function () {
            IPython.notebook.save_notebook();
            var project_name = prompt("Project name");
            var cell = IPython.notebook.insert_cell_below('code');
            cell.set_text(
                'import ipykee\n' +
                'ipykee.create_project_if_not_exist("' + project_name + '", repository=None, internal_path=".")\n' +
                'session = ipykee.Session(notebook="' + IPython.notebook.get_notebook_name() + '", project_name="' + project_name + '", docker_image=##PUT_HERE##)\n'
            );
        }
    },
    {
        'label'   : 'ipykee: commit',
        'icon'    : 'fa-magic', // select your icon from http://fortawesome.github.io/Font-Awesome/icons
        'callback': function () {
            IPython.notebook.save_notebook();
            var commit_message = prompt("Commit message");
            if (commit_message) {
                IPython.notebook.kernel.execute(
                    'com = session.commit("' + commit_message + '")\n' +
                    'print "Successfuly commited!\\nCommit message: \\"%s\\"\\nCommit hash: %s\\n" % (com[1], com[0])\n',
                    {
                        iopub : {
                            output : function(msg) {
                                var msg_type = msg.header.msg_type;
                                var content = msg.content;
                                if (msg_type === "error") {
                                    text = "Failed to commit!\n\n" + content.ename + ": " + content.evalue + "\n\n" + content.traceback.join("\n") + "\n";
                                } else {
                                    text = content.text + "\n";
                                }
                                console.log(msg)
                                console.log(content)
                                alert(text)
                            }
                        }
                    },
                    {silent: true, store_history: false, stop_on_error: true}
                )
            }
        }
    },
    ]);
