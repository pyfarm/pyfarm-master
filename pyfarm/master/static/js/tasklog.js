$(document).ready(function() {
    $.get("/api/v1/jobs/"+job_id+"/tasks/"+task_id+"/attempts/"+attempt+"/logs/"+log_identifier+"/logfile", function(data) {
        var timezone = moment.tz(tzdetect.matches()[0]).zoneAbbr();

        var data_length = data.length;
        var open_column = "";
        var open_row = [];
        var last_char = " ";
        var escaped = false;

        for(var i = 0 ; i < data_length ; i++) {
            if(!escaped && data.charAt(i) == "\"") {
                escaped = true;
                if(last_char == "\"")
                    open_column += "\"";
                }

            else if(escaped && data.charAt(i) == "\"") {
                escaped = false;
                }

            else if(!escaped && data.charAt(i) == ",") {
                open_row.push(open_column);
                open_column = "";
                }

            else if(data.charAt(i) == "\r") {
                // We just ignore CRs entirely
                }

            else if(!escaped && data.charAt(i) == "\n") {
                open_row.push(open_column);
                open_column = "";
                var new_tr = $("<tr></tr>");
                if(open_row.length > 0){
                    var timestamp_td = $("<td class='timestamp' title='Date and Time'></td>");
                    var nobr = $("<nobr></nobr>");
                    timestamp_td.append(nobr);
                    var utc = moment.utc(open_row[0] + "Z", moment.ISO_8601);
                    if(utc.isValid()) {
                        nobr.text(utc.local().format(timestamp_format)+" "+timezone);
                        }
                    new_tr.append(timestamp_td);
                    }
                if(open_row.length > 1){
                    var pid_td = $("<td class='pid' title='PID'></td>");
                    if(open_row[1] != "None")
                        pid_td.text(open_row[1]);
                    new_tr.append(pid_td);
                    }
                if(open_row.length > 2){
                    var stream_td = $("<td class='stream' title='Stream'></td>");
                    stream_td.text(open_row[2]);
                    new_tr.append(stream_td);
                    }
                if(open_row.length > 3){
                    var line_no_td = $("<td class='lineno' title='Line Number'></td>");
                    line_no_td.text(open_row[3]);
                    new_tr.append(line_no_td);
                    }
                if(open_row.length > 4){
                    var text_td = $("<td class='text' title='Text'></td>");
                    text_td.text(open_row[4]);
                    new_tr.append(text_td);
                    }
                $("#log_container table").append(new_tr);
                open_row = [];
                }

            else
                open_column += data.charAt(i);

            last_char = data.charAt(i);
            }
        });
    });
