$(document).ready(function() {
    $('.jobs_toggle').on('click', function(e) {
        var open = $(this).data("open") == "true";
        if(!open) {
            $(this).data("open", "true")
            $(this).removeClass("glyphicon-circle-arrow-down")
            $(this).addClass("glyphicon-circle-arrow-up")
            var jobgroupid = $(this).data("jobgroupid");
            var containing_td = $(this).closest("td");

            $.getJSON("/api/v1/jobgroups/" + jobgroupid + "/jobs", function(r) {
                var jobs_container = $("<div class='jobs_container'></div>");
                containing_td.append(jobs_container);

                for(var i = 0 ; i < r["jobs"].length ; ++i) {
                    var job = r["jobs"][i];
                    var job_div = $(
                        "<div class='panel'>"+
                          "<div class='panel-body'>"+
                            "<span class='glyphicon' title='failed'></span>"+
                            "<a href='/jobs/"+job["id"]+"'>"+job["title"]+"</a> ("+job["jobtype"]+")<br/>"+
                            "<div class='progress job_progress'>"+
                            "</div>"+
                          "</div>"+
                        "</div>");
                    jobs_container.append(job_div);
                    if(job["state"] == "queued") {
                        job_div.find("span.glyphicon").addClass("glyphicon-time");
                        job_div.find("div.panel").addClass("panel-info");
                    }
                    if(job["state"] == "running") {
                        job_div.find("span.glyphicon").addClass("glyphicon-play");
                        job_div.find("span.glyphicon").css("color", "#337AB7");
                        job_div.find("div.panel").addClass("panel-primary");
                    }
                    if(job["state"] == "failed") {
                        job_div.find("span.glyphicon").addClass("glyphicon-remove");
                        job_div.find("span.glyphicon").css("color", "#D9534F");
                        job_div.find("div.panel").addClass("panel-danger");
                    }
                    if(job["state"] == "done") {
                        job_div.find("span.glyphicon").addClass("glyphicon-ok");
                        job_div.find("span.glyphicon").css("color", "#5CB85C");
                        job_div.find("div.panel").addClass("panel-success");
                    }
                    if(job["tasks_done"] > 0) {
                        var percentage = (job["tasks_done"] / (job["tasks_queued"] + job["tasks_running"] + job["tasks_failed"] + job["tasks_done"])) * 100.0;
                        var progress_bar = $(
                            "<div class='progress-bar progress-bar-success' style='width:"+percentage+"%'>"+
                                "<span>"+percentage+"%</span>"+
                              "</div>");
                        job_div.find("div.job_progress").append(progress_bar);
                    }
                    if(job["tasks_failed"] > 0) {
                        var percentage = (job["tasks_failed"] / (job["tasks_queued"] + job["tasks_running"] + job["tasks_failed"] + job["tasks_done"])) * 100.0;
                        var progress_bar = $(
                            "<div class='progress-bar progress-bar-danger' style='width:"+percentage+"%'>"+
                                "<span>"+percentage+"%</span>"+
                              "</div>");
                        job_div.find("div.job_progress").append(progress_bar);
                    }
                    if(job["tasks_running"] > 0) {
                        var percentage = (job["tasks_running"] / (job["tasks_queued"] + job["tasks_running"] + job["tasks_failed"] + job["tasks_done"])) * 100.0;
                        var progress_bar = $(
                            "<div class='progress-bar progress-bar-striped' style='width:"+percentage+"%'>"+
                                "<span>"+percentage+"%</span>"+
                              "</div>");
                        job_div.find("div.job_progress").append(progress_bar);
                    }
                }
            });
        }
        else {
            $(this).data("open", "false");
            $(this).removeClass("glyphicon-circle-arrow-up")
            $(this).addClass("glyphicon-circle-arrow-down")
            $(this).closest("tr").find("div.jobs_container").remove();
        }
    });
});
