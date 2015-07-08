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
            return moment.unix(d).format('YYYY-MM-DD HH:mm');
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
