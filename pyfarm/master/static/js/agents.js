$(document).ready(function() {
    $('.all-agents-selector').change(function() {
        $('input.agent-selector').prop('checked', this.checked);
    });

    $('#selected-restart').click(function() {
        if(confirm('Are you sure you want to restart those agents?')) {
            var restart_form = $("#restart_multiple_form");
            $("input.agent-selector:checked").each(function() {
                var agent_input = $("<input type='hidden' name='agent_id' value='"+$(this).attr('value')+"'>");
                restart_form.append(agent_input);
            });
            restart_form.submit();
        }
    });

    $('#selected-disable').click(function() {
        if(confirm('Are you sure you want to disable those agents?')) {
            var disable_form = $("#disable_multiple_form");
            $("input.agent-selector:checked").each(function() {
                var agent_input = $("<input type='hidden' name='agent_id' value='"+$(this).attr('value')+"'>");
                disable_form.append(agent_input);
            });
            disable_form.submit();
        }
    });

    $('#selected-enable').click(function() {
        if(confirm('Are you sure you want to enable those agents?')) {
            var enable_form = $("#enable_multiple_form");
            $("input.agent-selector:checked").each(function() {
                var agent_input = $("<input type='hidden' name='agent_id' value='"+$(this).attr('value')+"'>");
                enable_form.append(agent_input);
            });
            enable_form.submit();
        }
    });

    $('#selected-delete').click(function() {
        if(confirm('Are you sure you want to delete those agents?')) {
            var delete_form = $("#delete_multiple_form");
            delete_form.children("input[name='agent_id']").remove();
           $("input.agent-selector:checked").each(function() {
                var agent_input = $("<input type='hidden' name='agent_id' value='"+$(this).attr('value')+"'>");
                delete_form.append(agent_input);
            });
            delete_form.submit();
        }
    });
});
