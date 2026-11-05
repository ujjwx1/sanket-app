export function overview(issues, now = new Date()) {
 const days = Array.from({length:7}, (_,i) => {const d=new Date(now); d.setHours(0,0,0,0); d.setDate(d.getDate()-6+i); return { date:d, count:0 }})
 for (const issue of issues) {const date=new Date(issue.created_at); const day=days.find(d=>d.date.getFullYear()===date.getFullYear() && d.date.getMonth()===date.getMonth() && d.date.getDate()===date.getDate());if(day)day.count++}
 return {total:issues.length,newCount:issues.filter(x=>x.status==='new').length,reviewed:issues.filter(x=>x.status==='reviewed').length,highPriority:issues.filter(x=>['high','critical'].includes(x.data?.severity)).length,days}
}
