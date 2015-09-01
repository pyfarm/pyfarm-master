$(document).ready(function() {
    nv.addGraph(function() {
        var chart = nv.models.multiBarChart()
            .margin({top: 30, right: 60, bottom: 50, left: 70})
            .stacked(true)
            .x(function(d,i) { return d[0] })
            .y(function(d,i) {return d[1] });

    chart.xAxis.tickFormat(function(d) {
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

    d3.select('#event_chart svg')
        .call(chart);

    nv.utils.windowResize(chart.update);

    return chart;
    });

    nv.addGraph(function() {
        var chart = nv.models.lineChart()
            .margin({top: 30, right: 60, bottom: 50, left: 70})
            .x(function(d,i) { return d[0] })
            .y(function(d,i) {return d[1] });

    chart.xAxis.tickFormat(function(d) {
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

    d3.select('#totals_chart svg')
        .call(chart);

    nv.utils.windowResize(chart.update);

    return chart;
  });

});
