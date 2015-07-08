$(document).ready(function() {
    nv.addGraph(function() {
    var chart = nv.models.multiBarChart()
                    .margin({left: 100})
                    .stacked(true)
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
