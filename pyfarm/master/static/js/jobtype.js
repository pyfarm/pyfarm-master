$(document).ready(function() {
    $("#software").change(function() {
        $("#minimum_version, #maximum_version").children("option").remove();
        var empty_option = $("<option></option>");
        $("#minimum_version, #maximum_version").append(empty_option);
        var software_id = $("#software").val()
        $.getJSON("/api/v1/software/"+software_id+"/versions/", function(r) {
            console.log(r);
            var empty_option = $("<option></option>");
            for(var i = 0; i < r.length ; i++) {
                console.log(r[i]);
                var option = $('<option value="'+r[i]['id']+'">'+r[i]['version']+'</option>');
                $("#minimum_version, #maximum_version").append(option);
            }
        });
    });
});
