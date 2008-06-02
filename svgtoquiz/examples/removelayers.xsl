<?xml version="1.0" encoding="utf-8"?>
<!-- Remove layers from an inkscape svg file, e.g.:
	xsltproc - -stringparam layers 'layer4|layer8|layer11|layer13' \
		 removelayers.xsl input.xml
     (the space between the first two hyphens must be removed)
-->
<xsl:stylesheet version="1.0"
		xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
		xmlns:svg="http://www.w3.org/2000/svg"
		xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
    <xsl:output method="xml" encoding="utf-8" standalone="no"/>
    <xsl:preserve-space elements="*"/>

    <xsl:template match="@* | node()">
	<xsl:if test="not(@inkscape:groupmode='layer' and contains($layers, @id))">
	    <xsl:copy>
		<xsl:apply-templates select="@* | node()"/>
	    </xsl:copy>
	</xsl:if>
    </xsl:template>

</xsl:stylesheet>
