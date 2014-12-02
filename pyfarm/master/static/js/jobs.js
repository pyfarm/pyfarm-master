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
            $(this).removeClass("icon-collapse-up")
            $(this).addClass("icon-collapse-down")
            $(this).closest("tr").find("table.subjob-table").remove();
        }
    });
});
