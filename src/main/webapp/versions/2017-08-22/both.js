
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-92184227-1', 'auto');
  ga('send', 'pageview');


function mo(elem) {    
    var  line =document.getElementsByTagName("line")
 
  elem.setAttribute("class","circle-active");
    for(i = 0; i < line.length; i++) {                                          
                                                                                
        if(line[i].getAttributeNode("targetId").value === elem.id) {            
            line[i].setAttribute("class","link-activeIncoming");
            document.getElementById(line[i].getAttributeNode("sourceId").value).setAttribute("class","circle-active");
        //    line[i].setAttribute("oldStroke",line[i].getAttributeNode("style").value);
         //   line[i].setAttribute("style","stroke-width: 10px");

        } 
        if(line[i].getAttributeNode("sourceId").value === elem.id) {            
            line[i].setAttribute("class","link-activeOutgoung");
            document.getElementById(line[i].getAttributeNode("targetId").value).setAttribute("class","circle-active");
     //       line[i].setAttribute("oldStroke",line[i].getAttributeNode("style").value);
         //   line[i].setAttribute("style","stroke-width: 10px");

        }
        if((line[i].getAttributeNode("targetId").value === elem.id)&&(line[i].getAttributeNode("sourceId").value === elem.id)) {            
            //alert(line[i])
            line[i].setAttribute("class","link-activeBoth");
             document.getElementById(line[i].getAttributeNode("targetId").value).setAttribute("class","circle-active");
             document.getElementById(line[i].getAttributeNode("sourceId").value).setAttribute("class","circle-active");
      //      line[i].setAttribute("oldStroke",line[i].getAttributeNode("style").value);
        //    line[i].setAttribute("style","stroke-width: 10px");

        }                                                                              
    }                                                                           
}

function mleave(elem) {                   
    elem.setAttribute("class","circle-pasive");                                      
    var line = document.getElementsByTagName("line");                           
    for(i = 0; i < line.length; i++) {                                          
                                                                                
        if(line[i].getAttributeNode("targetId").value === elem.id) {     
        document.getElementById(line[i].getAttributeNode("sourceId").value).setAttribute("class","circle-pasive");       
            //alert(line[i])
 //           line[i].setAttribute("style",line[i].getAttributeNode("style").value);
            line[i].setAttribute("class","link");       
        }
        if(line[i].getAttributeNode("sourceId").value === elem.id) {            
            document.getElementById(line[i].getAttributeNode("targetId").value).setAttribute("class","circle-pasive");
            //alert(line[i])
 //           line[i].setAttribute("style",line[i].getAttributeNode("style").value);
            line[i].setAttribute("class","link");       
        }                                                                          
    }                                                                           
}
