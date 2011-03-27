# -*- encoding: utf-8 -*-

des_xsd = '''\
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified">
	<xs:element name="fichier_des">
		<xs:annotation>
			<xs:documentation>fichier de déclarations de service</xs:documentation>
		</xs:annotation>
		<xs:complexType>
			<xs:sequence>
				<xs:element ref="declaration_des" maxOccurs="unbounded"/>
			</xs:sequence>
		</xs:complexType>
	</xs:element>
	<xs:element name="declaration_des">
		<xs:annotation>
			<xs:documentation>declaration de services </xs:documentation>
		</xs:annotation>
		<xs:complexType>
			<xs:sequence>
				<xs:element ref="num_des"/>
				<xs:element ref="num_tvaFr"/>
				<xs:element ref="mois_des"/>
				<xs:element ref="an_des"/>
				<xs:element ref="ligne_des" maxOccurs="unbounded"/>
			</xs:sequence>
		</xs:complexType>
	</xs:element>
	<xs:element name="num_des">
		<xs:annotation>
			<xs:documentation>numéro de la DES </xs:documentation>
		</xs:annotation>
		<xs:simpleType>
			<xs:restriction base="xs:positiveInteger">
				<xs:minInclusive value="1"/>
				<xs:maxInclusive value="999999"/>
			</xs:restriction>
		</xs:simpleType>
	</xs:element>
	<xs:element name="num_tvaFr">
		<xs:annotation>
			<xs:documentation>numéro TVA </xs:documentation>
		</xs:annotation>
		<xs:simpleType>
			<xs:restriction base="xs:string">
				<xs:pattern value="[F-f][R-r][0-9A-Za-z]{2}[0-9]{9}"/>
			</xs:restriction>
		</xs:simpleType>
	</xs:element>
	<xs:element name="mois_des">
		<xs:annotation>
			<xs:documentation>mois de la DES</xs:documentation>
		</xs:annotation>
		<xs:simpleType>
			<xs:restriction base="xs:string">
				<xs:length value="2"/>
				<xs:enumeration value="01"/>
				<xs:enumeration value="02"/>
				<xs:enumeration value="03"/>
				<xs:enumeration value="04"/>
				<xs:enumeration value="05"/>
				<xs:enumeration value="06"/>
				<xs:enumeration value="07"/>
				<xs:enumeration value="08"/>
				<xs:enumeration value="09"/>
				<xs:enumeration value="10"/>
				<xs:enumeration value="11"/>
				<xs:enumeration value="12"/>
			</xs:restriction>
		</xs:simpleType>
	</xs:element>
	<xs:element name="an_des">
		<xs:annotation>
			<xs:documentation>année de la DES</xs:documentation>
			<xs:documentation/>
		</xs:annotation>
		<xs:simpleType>
			<xs:restriction base="xs:string">
				<xs:pattern value="[2][0][1-9][0-9]"/>
			</xs:restriction>
		</xs:simpleType>
	</xs:element>
	<xs:element name="ligne_des">
		<xs:complexType>
			<xs:sequence>
				<xs:element ref="numlin_des"/>
				<xs:element ref="valeur"/>
				<xs:element ref="partner_des"/>
			</xs:sequence>
		</xs:complexType>
	</xs:element>
	<xs:element name="numlin_des">
		<xs:annotation>
			<xs:documentation>num de la ligne DES</xs:documentation>
		</xs:annotation>
		<xs:simpleType>
			<xs:restriction base="xs:positiveInteger">
				<xs:minInclusive value="1"/>
				<xs:maxInclusive value="999999"/>
			</xs:restriction>
		</xs:simpleType>
	</xs:element>
	<xs:element name="valeur">
		<xs:annotation>
			<xs:documentation>valeur de la ligne de DES</xs:documentation>
		</xs:annotation>
		<xs:simpleType>
			<xs:union>
				<xs:simpleType>
					<xs:restriction base="xs:negativeInteger">
						<xs:maxInclusive value="-1"/>
						<xs:minInclusive value="-9999999999"/>
					</xs:restriction>
				</xs:simpleType>
				<xs:simpleType>
					<xs:restriction base="xs:positiveInteger">
						<xs:minInclusive value="1"/>
						<xs:maxInclusive value="99999999999"/>
					</xs:restriction>
				</xs:simpleType>
			</xs:union>
		</xs:simpleType>
	</xs:element>
	<xs:element name="partner_des">
		<xs:annotation>
			<xs:documentation>partenaire</xs:documentation>
		</xs:annotation>
		<xs:simpleType>
			<xs:restriction base="xs:string">
				<xs:minLength value="7"/>
				<xs:maxLength value="14"/>
			</xs:restriction>
		</xs:simpleType>
	</xs:element>
</xs:schema>
'''
