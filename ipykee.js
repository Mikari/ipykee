// leave at least 2 line with only a star on it below, or doc generation fails
/**
*
*
* Ipykee button
*/


    IPython.toolbar.add_buttons_group([
    {
        'label'   : 'ipykee: commit',
        'icon'    : 'icon-arrow-up', // select your icon from http://fortawesome.github.io/Font-Awesome/icons
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
                                if (msg_type === "pyerr") {
                                    text = "Failed to commit!\n\n" + content.ename + ": " + content.evalue + "\n\n" + content.traceback.join("\n") + "\n";
                                } else {
                                    text = content.data + "\n";
                                }
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
