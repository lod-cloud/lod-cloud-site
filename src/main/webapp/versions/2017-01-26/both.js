function mo(elem) {    

    var line = document.getElementsByTagName("line");                           
    for(i = 0; i < line.length; i++) {                                          
                                                                                
        if(line[i].getAttributeNode("targetId").value === elem.id) {            
            line[i].setAttribute("class","link-activeIncoming");
            line[i].setAttribute("oldStroke",line[i].getAttributeNode("style").value);
            line[i].setAttribute("style","stroke-width: 10px");

        } 
        if(line[i].getAttributeNode("sourceId").value === elem.id) {            
            line[i].setAttribute("class","link-activeOutgoung");
            line[i].setAttribute("oldStroke",line[i].getAttributeNode("style").value);
            line[i].setAttribute("style","stroke-width: 10px");

        }
        if((line[i].getAttributeNode("targetId").value === elem.id)&&(line[i].getAttributeNode("sourceId").value === elem.id)) {            
            //alert(line[i])
            line[i].setAttribute("class","link-activeBoth");
            line[i].setAttribute("oldStroke",line[i].getAttributeNode("style").value);
            line[i].setAttribute("style","stroke-width: 10px");

        }                                                                              
    }                                                                           
}

function mleave(elem) {                                                             
    var line = document.getElementsByTagName("line");                           
    for(i = 0; i < line.length; i++) {                                          
                                                                                
        if(line[i].getAttributeNode("targetId").value === elem.id) {            
            //alert(line[i])
            line[i].setAttribute("style",line[i].getAttributeNode("style").value);
            line[i].setAttribute("class","active");       
        }
        if(line[i].getAttributeNode("sourceId").value === elem.id) {            
            //alert(line[i])
            line[i].setAttribute("style",line[i].getAttributeNode("style").value);
            line[i].setAttribute("class","active");       
        }                                                                          
    }                                                                           
}
