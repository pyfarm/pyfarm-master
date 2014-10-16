$(document).ready(function() {
    $("#add_software_sw").change(function() {
        var version_select =　$("#add_software_version")
        version_select.children("option").remove();

        var empty_option = $("<option></option>");
        version_select.append(empty_option);
        var software_id = $("#add_software_sw").val()
        if(software_id != '') {
            $.getJSON("/api/v1/software/"+software_id+"/versions/", function(r) {
                var empty_option = $("<option></option>");
                for(var i = 0; i < r.length ; i++) {
                    var option = $('<option value="'+r[i]['id']+'">'+r[i]['version']+'</option>');
                    version_select.append(option);
                }
            });
        }
    });
});
