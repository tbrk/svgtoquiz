(: xqilla -i <inputfile> inkscapeids.xql :)
declare namespace inkscape="http://www.inkscape.org/namespaces/inkscape";
declare namespace svg="http://www.w3.org/2000/svg";

(: List Inkscape layers in an svg file :)
for $x in //svg:g | //svg:path
where $x/@inkscape:label
return concat(data($x/@id), ", ",  data($x/@inkscape:label))
(: return (data($x/@id), data($x/@inkscape:label)) :)

