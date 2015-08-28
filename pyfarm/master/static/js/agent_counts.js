$(document).ready(function() {
    nv.addGraph(function() {
    if(area_chart) {
        var chart = nv.models.stackedAreaChart();
        }
    else {
        var chart = nv.models.multiBarChart()
                        .stacked(true);
        }
        chart.margin({left: 100})
             .x(function(d) { return d[0] })
             .y(function(d) { return d[1] })
             .showLegend(true)
             .showControls(true)
             .showYAxis(true)
             .showXAxis(true);

    chart.xAxis
        .axisLabel('Time ('+timezone+')')
        .tickFormat(function(d) {
        if(days_back < 3)
            {
            return moment.unix(d).format('HH:mm');
            }
        else if(days_back < 15)
            {
            return moment.unix(d).format('ddd HH:mm');
            }
        else if(days_back < 366)
            {
            return moment.unix(d).format('MMM Do');
            }
        else
            {
            return moment.unix(d).format('MMM YYYY');
            }
        });

    chart.yAxis
        .axisLabel('Number of Agents');

    // Render the chart
    d3.select('#chart svg').call(chart);

    //Update the chart when window resizes.
    nv.utils.windowResize(function() { chart.update() });
    return chart;
    });
});
