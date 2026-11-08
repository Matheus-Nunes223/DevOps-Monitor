(() => {
  const instances=new Map();
  const palette={green:'#58c894',blue:'#7fa9e8',yellow:'#d9ad59',red:'#dd7077',purple:'#aa8ec6',muted:'#7f8c99',grid:'#25313b',panel:'#111922'};
  const axisFont={family:'DM Sans, sans-serif',size:10};
  const tooltip={backgroundColor:'#17212b',borderColor:'#33414d',borderWidth:1,titleColor:'#e0e7ec',bodyColor:'#b7c2cb',padding:10,displayColors:true,boxWidth:7,boxHeight:7,cornerRadius:6};

  function destroy(id){const chart=instances.get(id);if(chart){chart.destroy();instances.delete(id)}}
  function destroyAll(){instances.forEach(chart=>chart.destroy());instances.clear()}
  function baseOptions(extra={}){
    return{responsive:true,maintainAspectRatio:false,resizeDelay:80,animation:{duration:240},interaction:{intersect:false,mode:'index'},plugins:{legend:{display:false,position:'bottom',labels:{color:'#8f9ca8',boxWidth:7,boxHeight:7,usePointStyle:true,pointStyle:'circle',padding:16,font:axisFont}},tooltip},scales:{x:{grid:{display:false},ticks:{color:'#778592',maxTicksLimit:7,maxRotation:0,font:axisFont},border:{display:false}},y:{beginAtZero:false,grid:{color:palette.grid,drawTicks:false},ticks:{color:'#778592',maxTicksLimit:5,padding:8,font:axisFont},border:{display:false}}},...extra};
  }
  function make(id,labels,datasets,type='line',options={}){
    const canvas=document.getElementById(id),ChartConstructor=window.Chart;
    if(!canvas||!ChartConstructor)return null;
    destroy(id);
    const isBar=type==='bar';
    const styled=datasets.map((item,index)=>{
      const color=item.color||[palette.green,palette.blue,palette.yellow,palette.purple][index%4];
      return{label:item.label,data:item.data,borderColor:color,backgroundColor:item.fill?`${color}20`:isBar?`${color}bb`:color,borderWidth:isBar?0:1.8,pointRadius:0,pointHoverRadius:3,tension:.34,fill:Boolean(item.fill),...(isBar?{borderRadius:3,barPercentage:.62,categoryPercentage:.72}:{})};
    });
    const chart=new ChartConstructor(canvas,{type,data:{labels,datasets:styled},options:baseOptions({scales:{x:{grid:{display:false},ticks:{color:'#778592',maxTicksLimit:7,maxRotation:0,font:axisFont},border:{display:false}},y:{beginAtZero:options.beginAtZero??false,grid:{color:palette.grid,drawTicks:false},ticks:{color:'#778592',maxTicksLimit:5,padding:8,font:axisFont,callback:options.tick||((value)=>value)},border:{display:false}}},plugins:{...baseOptions().plugins,legend:{...baseOptions().plugins.legend,display:datasets.length>1}},...(options.extra||{})})});
    instances.set(id,chart);return chart;
  }
  function line(id,labels,datasets,options={}){return make(id,labels,datasets,'line',options)}
  function bar(id,labels,datasets,options={}){return make(id,labels,datasets,'bar',options)}
  function doughnut(id,labels,values){
    const canvas=document.getElementById(id),ChartConstructor=window.Chart;
    if(!canvas||!ChartConstructor)return null;
    destroy(id);
    const chart=new ChartConstructor(canvas,{type:'doughnut',data:{labels,datasets:[{data:values,backgroundColor:[palette.green,palette.blue,palette.yellow,palette.red,palette.purple],borderColor:palette.panel,borderWidth:3,hoverOffset:3}]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:240},cutout:'76%',plugins:{legend:{position:'right',labels:{color:'#9aa6b0',boxWidth:7,boxHeight:7,usePointStyle:true,pointStyle:'circle',padding:13,font:axisFont}},tooltip}}});
    instances.set(id,chart);return chart;
  }
  window.DevOpsCharts={destroyAll,line,bar,doughnut,palette};
})();
