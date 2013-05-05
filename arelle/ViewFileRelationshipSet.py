'''
Created on Oct 6, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from arelle import ModelObject, ModelDtsObject, XbrlConst, XmlUtil, ViewFile
from arelle.ModelDtsObject import ModelRelationship
import os

def viewRelationshipSet(modelXbrl, outfile, header, arcrole, linkrole=None, linkqname=None, arcqname=None, labelrole=None, lang=None):
    modelXbrl.modelManager.showStatus(_("viewing relationships {0}").format(os.path.basename(arcrole)))
    view = ViewRelationshipSet(modelXbrl, outfile, header, labelrole, lang)
    view.view(arcrole, linkrole, linkqname, arcqname)
    view.close()
    
class ViewRelationshipSet(ViewFile.View):
    def __init__(self, modelXbrl, outfile, header, labelrole, lang):
        super(ViewRelationshipSet, self).__init__(modelXbrl, outfile, header, lang)
        self.labelrole = labelrole
        self.isResourceArcrole = False
        
    def view(self, arcrole, linkrole=None, linkqname=None, arcqname=None):
        # determine relationships indent depth for dimensions linkbases
        # set up treeView widget and tabbed pane
        if arcrole == XbrlConst.parentChild: # extra columns
            heading = ["Presentation Relationships", "Type", "References"]
        elif arcrole == XbrlConst.summationItem:    # add columns for calculation relationships
            heading = ["Calculation Relationships", "Weight", "Balance"]
        if arcrole == "XBRL-dimensions":    # add columns for dimensional information
            heading = ["Dimensions Relationships", "Arcrole","CntxElt","Closed","Usable"]
        elif isinstance(arcrole, (list,tuple)) or XbrlConst.isResourceArcrole(arcrole):
            self.isResourceArcrole = True
            self.showReferences = isinstance(arcrole, _STR_BASE) and arcrole.endswith("-reference")
            heading = ["Resource Relationships", "Arcrole","Resource","ResourceRole","Language"]
        else:
            heading = [os.path.basename(arcrole).title() + " Relationships"]
        # relationship set based on linkrole parameter, to determine applicable linkroles
        relationshipSet = self.modelXbrl.relationshipSet(arcrole, linkrole, linkqname, arcqname)

        self.arcrole = arcrole
        
        if relationshipSet:
            # sort URIs by definition
            linkroleUris = []
            for linkroleUri in relationshipSet.linkRoleUris:
                modelRoleTypes = self.modelXbrl.roleTypes.get(linkroleUri)
                if modelRoleTypes:
                    roledefinition = (modelRoleTypes[0].genLabel(lang=self.lang, strip=True) or modelRoleTypes[0].definition or linkroleUri)                    
                else:
                    roledefinition = linkroleUri
                linkroleUris.append((roledefinition, linkroleUri))
            linkroleUris.sort()
    
            for roledefinition, linkroleUri in linkroleUris:
                linkRelationshipSet = self.modelXbrl.relationshipSet(arcrole, linkroleUri, linkqname, arcqname)
                for rootConcept in linkRelationshipSet.rootConcepts:
                    self.treeDepth(rootConcept, rootConcept, 2, arcrole, linkRelationshipSet, set())
                    
        self.addRow(heading, asHeader=True) # must do after determining tree depth
        
        if relationshipSet:
            # for each URI in definition order
            for roledefinition, linkroleUri in linkroleUris:
                attr = {"role": linkroleUri}
                self.addRow([roledefinition], treeIndent=0, colSpan=len(heading), 
                            xmlRowElementName="linkRole", xmlRowEltAttr=attr, xmlCol0skipElt=True)
                linkRelationshipSet = self.modelXbrl.relationshipSet(arcrole, linkroleUri, linkqname, arcqname)
                for rootConcept in linkRelationshipSet.rootConcepts:
                    self.viewConcept(rootConcept, rootConcept, "", self.labelrole, 1, arcrole, linkRelationshipSet, set())

    def treeDepth(self, concept, modelObject, indent, arcrole, relationshipSet, visited):
        if concept is None:
            return
        if indent > self.treeCols: self.treeCols = indent
        if concept not in visited:
            visited.add(concept)
            for modelRel in relationshipSet.fromModelObject(concept):
                targetRole = modelRel.targetRole
                if targetRole is None or len(targetRole) == 0:
                    targetRole = relationshipSet.linkrole
                    nestedRelationshipSet = relationshipSet
                else:
                    nestedRelationshipSet = self.modelXbrl.relationshipSet(arcrole, targetRole)
                self.treeDepth(modelRel.toModelObject, modelRel, indent + 1, arcrole, nestedRelationshipSet, visited)
            visited.remove(concept)
            
    def viewConcept(self, concept, modelObject, labelPrefix, preferredLabel, indent, arcrole, relationshipSet, visited):
        try:
            if concept is None:
                return
            isRelation = isinstance(modelObject, ModelRelationship)
            if isinstance(concept, ModelDtsObject.ModelConcept):
                text = labelPrefix + concept.label(preferredLabel,lang=self.lang,linkroleHint=relationshipSet.linkrole)
                if (self.arcrole in ("XBRL-dimensions", XbrlConst.hypercubeDimension) and
                    concept.isTypedDimension and 
                    concept.typedDomainElement is not None):
                    text += " (typedDomain={0})".format(concept.typedDomainElement.qname)  
                xmlRowElementName = "concept"
                attr = {"name": str(concept.qname)}
            elif self.arcrole == "Table-rendering":
                text = concept.localName
                xmlRowElementName = "element"
                attr = {"label": concept.xlinkLabel}
            elif isinstance(concept, ModelDtsObject.ModelResource):
                if self.showReferences:
                    text = (concept.viewText().strip() or concept.localName)
                    attr = {"text": text,
                            "innerXml": XmlUtil.xmlstring(concept, stripXmlns=True, prettyPrint=False, contentsOnly=True)}
                else:
                    text = (concept.elementText.strip() or concept.localName)
                    attr = {"text": text}
                xmlRowElementName = "resource"
            else:   # just a resource
                text = concept.localName
                xmlRowElementName = text
            cols = [text]
            if isRelation:
                if arcrole == "XBRL-dimensions": # extra columns
                    relArcrole = modelObject.arcrole
                    cols.append( os.path.basename( relArcrole ) )
                    if relArcrole in (XbrlConst.all, XbrlConst.notAll):
                        cols.append( modelObject.contextElement )
                        cols.append( modelObject.closed )
                    else:
                        cols.append(None)
                        cols.append(None)
                    if relArcrole in (XbrlConst.dimensionDomain, XbrlConst.domainMember):
                        cols.append( modelObject.usable  )
            if self.arcrole == XbrlConst.parentChild: # extra columns
                cols.append(concept.niceType)
                cols.append(concept.viewReferences(concept))
            elif arcrole == XbrlConst.summationItem:
                if isRelation:
                    cols.append("{:0g} ".format(modelObject.weight))
                else:
                    cols.append("") # no weight on roots
                cols.append(concept.balance)
            elif self.isResourceArcrole: # resource columns
                if isRelation:
                    cols.append(modelObject.arcrole)
                else:
                    cols.append("") # no weight on roots
                if isinstance(concept, ModelDtsObject.ModelResource):
                    cols.append(concept.localName)
                    cols.append(concept.role or '')
                    cols.append(concept.xmlLang)
            self.addRow(cols, treeIndent=indent, xmlRowElementName=xmlRowElementName, xmlRowEltAttr=attr, xmlCol0skipElt=True)
            if concept not in visited:
                visited.add(concept)
                for modelRel in relationshipSet.fromModelObject(concept):
                    nestedRelationshipSet = relationshipSet
                    targetRole = modelRel.targetRole
                    if arcrole == XbrlConst.summationItem:
                        childPrefix = "({:0g}) ".format(modelRel.weight) # format without .0 on integer weights
                    elif targetRole is None or len(targetRole) == 0:
                        targetRole = relationshipSet.linkrole
                        childPrefix = ""
                    else:
                        nestedRelationshipSet = self.modelXbrl.relationshipSet(arcrole, targetRole)
                        childPrefix = "(via targetRole) "
                    toConcept = modelRel.toModelObject
                    if toConcept in visited:
                        childPrefix += "(loop) "
                    self.viewConcept(toConcept, modelRel, childPrefix, (modelRel.preferredLabel or self.labelrole), indent + 1, arcrole, nestedRelationshipSet, visited)
                visited.remove(concept)
        except AttributeError: #  bad relationship
            return