$(document).ready(function() {
    $('.dropdown-menu').on('click', function(e) {
        if($(this).hasClass('dropdown-menu-form')) {
            e.stopPropagation();
        }
    });

    $('.subjob_toggle').on('click', function(e) {
        var open = $(this).data("open") == "true";
        if(!open) {
            $(this).data("open", "true")
            $(this).removeClass("icon-circle-arrow-down")
            $(this).addClass("icon-circle-arrow-up")
            var jobid = $(this).data("jobid");
            var subjob_table = $(
                "<table class='table table-striped table-bordered subjob-table'>"+
                "</table>");
            $(this).closest("td").append(subjob_table);

            $.getJSON("/api/v1/jobs/" + jobid, function(r) {
                for(var i = 0 ; i < r["children"].length ; ++i) {
                    var child = r["children"][i];
                    $.getJSON("/api/v1/jobs/" + child["id"], function(s) {
                        var subjob_row = $(
                            "<tr>"+
                              "<td><a href='/jobs/"+s["id"]+"'>"+s["title"]+"</td>"+
                              "<td>"+s["jobtype"]+"</td>"+
                              "<td>"+s["state"]+"</td>"+
                            "</tr>");
                        subjob_table.append(subjob_row);
                    });
                }
            });
        }
        else {
            $(this).data("open", "false");
            $(this).removeClass("icon-circle-arrow-up")
            $(this).addClass("icon-circle-arrow-down")
            $(this).closest("tr").find("table.subjob-table").remove();
        }
    });

    $('.all-jobs-selector').change(function() {
        $('input.job-selector').prop('checked', this.checked);
    });

    $('#selected-rerun').click(function() {
        if(confirm('Are you sure you want to rerun those jobs? This will include all tasks, even those already done.')) {
            var rerun_form = $("#rerun_multiple_form");
            $("input.job-selector:checked").each(function() {
                var job_input = $("<input type='hidden' name='job_id' value='"+$(this).attr('value')+"'>");
                rerun_form.append(job_input);
            });
            rerun_form.submit();
        }
    });

    $('#selected-rerun-failed').click(function() {
        if(confirm('Are you sure you want to rerun those jobs? Only the tasks that are failed will be rerun.')) {
            var rerun_form = $("#rerun_failed_multiple_form");
            $("input.job-selector:checked").each(function() {
                var job_input = $("<input type='hidden' name='job_id' value='"+$(this).attr('value')+"'>");
                rerun_form.append(job_input);
            });
            rerun_form.submit();
        }
    });

    $('#selected-pause').click(function() {
        if(confirm('Are you sure you want to pause those jobs?')) {
            var pause_form = $("#pause_multiple_form");
            $("input.job-selector:checked").each(function() {
                var job_input = $("<input type='hidden' name='job_id' value='"+$(this).attr('value')+"'>");
                pause_form.append(job_input);
            });
            pause_form.submit();
        }
    });

    $('#selected-resume').click(function() {
        if(confirm('Are you sure you want to resume those jobs?')) {
            var resume_form = $("#resume_multiple_form");
            $("input.job-selector:checked").each(function() {
                var job_input = $("<input type='hidden' name='job_id' value='"+$(this).attr('value')+"'>");
                resume_form.append(job_input);
            });
            resume_form.submit();
        }
    });
});
