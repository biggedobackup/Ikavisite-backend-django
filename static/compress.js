var _uploading=false;
function compressAndUploadLogo(input, form){
  if(_uploading)return;
  var file=input.files[0];
  if(!file)return;
  _uploading=true;
  var text=input.parentNode.querySelector('.ent-logo-text');
  if(text)text.textContent='Compression...';
  var reader=new FileReader();
  reader.onload=function(e){
    var img=new Image();
    img.onerror=function(){_uploading=false;if(text)text.textContent='Changer le logo';};
    img.onload=function(){
      var canvas=document.createElement('canvas');
      var MAX=800,ratio=1;
      if(img.width>MAX)ratio=MAX/img.width;
      else if(img.height>MAX)ratio=MAX/img.height;
      canvas.width=Math.round(img.width*ratio);
      canvas.height=Math.round(img.height*ratio);
      var ctx=canvas.getContext('2d');
      ctx.drawImage(img,0,0,canvas.width,canvas.height);
      canvas.toBlob(function(blob){
        if(!blob){_uploading=false;if(text)text.textContent='Changer le logo';return;}
        var compressed=new File([blob],file.name.replace(/\.[^.]+$/,'.jpg'),{type:'image/jpeg',lastModified:Date.now()});
        var dt=new DataTransfer();
        dt.items.add(compressed);
        input.files=dt.files;
        if(text)text.textContent='Téléchargement...';
        form.submit();
      },'image/jpeg',0.8);
    };
    img.src=e.target.result;
  };
  reader.onerror=function(){_uploading=false;if(text)text.textContent='Changer le logo';};
  reader.readAsDataURL(file);
}
