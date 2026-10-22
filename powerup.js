const ICON='./icon.svg';
function openAction(t,mode){return t.popup({title:mode==='open'?'Open Existing PureRef Board':'Send to PureRef',url:'./action.html',args:{mode},height:410});}
window.TrelloPowerUp.initialize({
 'card-buttons':function(t){
   if(!t.isMemberSignedIn()) return [];
   return t.get('member','private','pureRefEnabled',false).then(function(enabled){
     if(!enabled) return [];
     return [
       {icon:ICON,text:'Send to PureRef',condition:'always',callback:function(t2){return openAction(t2,'send');}},
       {icon:ICON,text:'Open PureRef',condition:'always',callback:function(t2){return openAction(t2,'open');}}
     ];
   }).catch(function(){return [];});
 },
 'show-settings':function(t){return t.popup({title:'Send to PureRef — My Settings',url:'./settings.html',height:520});}
});