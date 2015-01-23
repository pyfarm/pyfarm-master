$(document).ready(function() {
    $("#software").change(function() {
        $("#minimum_version, #maximum_version").children("option").remove();
        var empty_option = $("<option></option>");
        $("#minimum_version, #maximum_version").append(empty_option);
        var software_id = $("#software").val()
        $.getJSON("/api/v1/software/"+software_id+"/versions/", function(r) {
            var empty_option = $("<option></option>");
            for(var i = 0; i < r.length ; i++) {
                var option = $('<option value="'+r[i]['id']+'">'+r[i]['version']+'</option>');
                $("#minimum_version, #maximum_version").append(option);
            }
        });
    });

    $("#add_sw_req").click(function() {
        $.getJSON("/api/v1/software/", function(r) {
            var new_row = $("<tr>"+
                              "<td>"+
                                "<i class='glyphicon glyphicon-remove clickable-icon' title='Remove'></i>"+
                              "</td>"+
                              "<td>"+
                                "<select class='software form-control' name='software'></select>"+
                              "</td>"+
                              "<td>"+
                                "<nobr>&gt;= <select class='min_version form-control' style='display: inline;' name='min_version'></select></nobr>"+
                              "</td>"+
                              "<td>"+
                                "<nobr>&lt;= <select class='max_version form-control' style='display: inline;' name='max_version'></select></nobr>"+
                              "</td>"+
                            "</tr>");

            var software_select = new_row.find("select.software");
            for(var i = 0; i < r.length ; i++) {
                var option = $('<option value="'+r[i]['id']+'">'+r[i]['software']+'</option>');
                software_select.append(option);
            }

            software_select.change(function() {
                var software_id = $(this).val();
                var target = $(this).closest("tr");
                var version_selects = target.find("select.min_version, select.max_version");
                version_selects.children("option").remove();
                $.getJSON("/api/v1/software/"+software_id+"/versions/", function(r) {
                    var empty_option = $("<option></option>");
                    version_selects.append(empty_option);
                    for(var i = 0; i < r.length ; i++) {
                        var option = $('<option value="'+r[i]['id']+'">'+r[i]['version']+'</option>');
                        version_selects.append(option);
                    }
                });
            });

            var remove_button = new_row.find("i.icon-remove")
            remove_button.click(function() {
                $(this).closest("tr").remove();
            });

            $("#add_sw_req").closest("tr").before(new_row);
            software_select.change();
        });
    });
});
