#!/usr/bin/env node
'use strict';

// These in-memory stubs are assumptions for static checks, NOT SAP API exports.
// No generated source, dependencies or credentials are written to disk.
const fs = require('node:fs');
const path = require('node:path');
if (!process.argv[2]) {
  console.error('Usage: node Validation/validate-email.cjs /path/to/@abaplint/core');
  process.exit(2);
}
const core = require(path.resolve(process.argv[2]));
const root = path.resolve(__dirname, '..');
const sources = [
  ['ZIF_FI_DAS_EMAIL', 'zif_fi_das_email.intf.abap'],
  ['ZCL_FI_DAS_EMAIL', 'zcl_fi_das_email.clas.abap'],
  ['ZCL_FI_DAS_EMAIL test classes', 'zcl_fi_das_email.clas.testclasses.abap'],
];

function registry(rules) {
  const config = core.Config.getDefault().get();
  config.dependencies = [];
  config.syntax.version = core.Version.v750;
  config.rules = rules;
  return new core.Registry(new core.Config(JSON.stringify(config)));
}
function add(reg, filename, content) {
  reg.addFile(new core.MemoryFile(filename, content));
}
function addSources(reg) {
  for (const [source, filename] of sources) {
    add(reg, filename, fs.readFileSync(path.join(root, 'ABAP code', source), 'utf8'));
  }
}
function check(reg, label) {
  reg.parse();
  const issues = reg.findIssues();
  for (const issue of issues) {
    console.error(`${issue.getFilename()}:${issue.getStart().getRow()}: ${issue.getMessage()}`);
  }
  console.log(`${label}: ${issues.length} issue(s)`);
  if (issues.length) process.exitCode = 1;
}
function xml(content) {
  return `<abapGit><asx:abap xmlns:asx="http://www.sap.com/abapxml"><asx:values>${content}</asx:values></asx:abap></abapGit>`;
}
function dataElement(reg, name, datatype, length) {
  add(reg, `${name}.dtel.xml`, xml(`<DD04V><ROLLNAME>${name.toUpperCase()}</ROLLNAME><DATATYPE>${datatype}</DATATYPE><LENG>${length}</LENG></DD04V>`));
}
function table(reg, name, fields, category = 'TRANSP') {
  const body = fields.map(([field, datatype, length, key = '']) =>
    `<DD03P><FIELDNAME>${field.toUpperCase()}</FIELDNAME><DATATYPE>${datatype}</DATATYPE><LENG>${length}</LENG><KEYFLAG>${key}</KEYFLAG></DD03P>`).join('');
  add(reg, `${name}.tabl.xml`, xml(`<DD02V><TABNAME>${name.toUpperCase()}</TABNAME><TABCLASS>${category}</TABCLASS></DD02V><DD03P_TABLE>${body}</DD03P_TABLE>`));
}
function tableType(reg, name, rowtype) {
  add(reg, `${name}.ttyp.xml`, xml(`<DD40V><TYPENAME>${name.toUpperCase()}</TYPENAME><ROWTYPE>${rowtype.toUpperCase()}</ROWTYPE><ROWKIND>S</ROWKIND><DATATYPE>STRU</DATATYPE><ACCESSMODE>T</ACCESSMODE><KEYDEF>D</KEYDEF><KEYKIND>N</KEYKIND></DD40V>`));
}
function classStub(reg, name, definition) {
  const methods = [...definition.matchAll(/(?:CLASS-)?METHODS\s+(\w+)/g)]
    .map(match => `METHOD ${match[1]}. ENDMETHOD.`).join('\n');
  add(reg, `${name}.clas.abap`, `CLASS ${name} DEFINITION PUBLIC. PUBLIC SECTION. ${definition} ENDCLASS.
    CLASS ${name} IMPLEMENTATION. ${methods} ENDCLASS.`);
}
function addStubs(reg) {
  for (const [name, type, length] of [
    ['so_obj_tp', 'CHAR', 3], ['so_obj_des', 'CHAR', 50],
    ['so_obj_len', 'NUMC', 12],
  ]) dataElement(reg, name, type, length);
  table(reg, 'adr6', [['smtp_addr', 'CHAR', 241]], 'INTTAB');
  table(reg, 'soli', [['line', 'CHAR', 255]], 'INTTAB');
  table(reg, 'solix', [['line', 'RAW', 255]], 'INTTAB');
  tableType(reg, 'soli_tab', 'soli');
  tableType(reg, 'solix_tab', 'solix');
  table(reg, 'match_result', [['offset', 'INT4', 10], ['length', 'INT4', 10]], 'INTTAB');
  tableType(reg, 'match_result_tab', 'match_result');
  table(reg, 'zfi_das_email', [
    ['mandt', 'CLNT', 3, 'X'], ['template_name', 'CHAR', 100, 'X'],
    ['language', 'CHAR', 5, 'X'], ['subject', 'CHAR', 1024],
    ['body', 'STRG', 0], ['status', 'CHAR', 10],
  ]);
  table(reg, 'zfi_das_conf_val', [
    ['mandt', 'CLNT', 3, 'X'], ['config_name', 'CHAR', 100, 'X'],
    ['config_value', 'CHAR', 1024],
  ]);
  table(reg, 'zfi_das_usr_lang', [
    ['mandt', 'CLNT', 3, 'X'], ['email_id', 'CHAR', 241, 'X'],
    ['language', 'CHAR', 5],
  ]);

  classStub(reg, 'cx_root', `
    METHODS constructor IMPORTING previous TYPE REF TO cx_root OPTIONAL.
    METHODS get_text RETURNING VALUE(result) TYPE string.`);
  for (const name of ['cx_static_check', 'cx_dynamic_check']) {
    add(reg, `${name}.clas.abap`, `CLASS ${name} DEFINITION PUBLIC INHERITING FROM cx_root. ENDCLASS.
      CLASS ${name} IMPLEMENTATION. ENDCLASS.`);
  }
  for (const name of ['cx_bcs', 'cx_sy_open_sql_db']) {
    add(reg, `${name}.clas.abap`, `CLASS ${name} DEFINITION PUBLIC INHERITING FROM cx_dynamic_check. ENDCLASS.
      CLASS ${name} IMPLEMENTATION. ENDCLASS.`);
  }
  add(reg, 'if_t100_dyn_msg.intf.abap', 'INTERFACE if_t100_dyn_msg PUBLIC. ENDINTERFACE.');
  add(reg, 'zcx_fi_das_error.clas.abap',
    fs.readFileSync(path.join(root, 'ABAP code', 'ZCX_FI_DAS_ERROR'), 'utf8'));

  classStub(reg, 'cl_abap_char_utilities', `
    CONSTANTS cr_lf TYPE c LENGTH 2 VALUE %_CR_LF.
    CONSTANTS newline TYPE c LENGTH 1 VALUE %_NEWLINE.`);
  classStub(reg, 'cl_bcs_convert', `
    CLASS-METHODS xstring_to_solix IMPORTING iv_xstring TYPE xstring
      RETURNING VALUE(et_solix) TYPE solix_tab.
    CLASS-METHODS string_to_soli IMPORTING iv_string TYPE string
      RETURNING VALUE(et_soli) TYPE soli_tab.`);
  classStub(reg, 'cl_cam_address_bcs', `
    CLASS-METHODS create_internet_address IMPORTING i_address TYPE adr6-smtp_addr
      RETURNING VALUE(result) TYPE REF TO cl_cam_address_bcs RAISING cx_bcs.`);
  classStub(reg, 'cl_document_bcs', `
    CLASS-METHODS create_document
      IMPORTING i_type TYPE so_obj_tp i_subject TYPE so_obj_des
                i_text TYPE soli_tab
      RETURNING VALUE(result) TYPE REF TO cl_document_bcs RAISING cx_bcs.
    METHODS add_attachment
      IMPORTING i_attachment_type TYPE so_obj_tp i_attachment_subject TYPE so_obj_des
                i_attachment_size TYPE so_obj_len i_attachment_header TYPE soli_tab
                i_att_content_hex TYPE solix_tab RAISING cx_bcs.`);
  classStub(reg, 'cl_bcs', `
    CLASS-METHODS create_persistent RETURNING VALUE(result) TYPE REF TO cl_bcs RAISING cx_bcs.
    METHODS set_document IMPORTING i_document TYPE REF TO cl_document_bcs RAISING cx_bcs.
    METHODS set_message_subject IMPORTING ip_subject TYPE string RAISING cx_bcs.
    METHODS set_sender IMPORTING i_sender TYPE REF TO cl_cam_address_bcs RAISING cx_bcs.
    METHODS add_recipient
      IMPORTING i_recipient TYPE REF TO cl_cam_address_bcs i_copy TYPE abap_bool
                i_blind_copy TYPE abap_bool RAISING cx_bcs.
    METHODS send IMPORTING i_with_error_screen TYPE abap_bool
      RETURNING VALUE(result) TYPE abap_bool RAISING cx_bcs.`);
  classStub(reg, 'cl_abap_unit_assert', `
    CLASS-METHODS assert_equals IMPORTING act TYPE any exp TYPE any msg TYPE string OPTIONAL.
    CLASS-METHODS fail IMPORTING msg TYPE string.`);
}

console.log(`@abaplint/core ${require(path.join(path.resolve(process.argv[2]), 'package.json')).version}; target v750`);
const parser = registry({ parser_error: true });
addSources(parser);
check(parser, 'Unstubbed production/test parsing');
const syntax = registry({ parser_error: true, check_syntax: true });
addSources(syntax);
addStubs(syntax);
check(syntax, 'Syntax/type check WITH ASSUMED SAP/DDIC STUBS');
console.log('ABAP Unit and SAP/BCS runtime NOT executed; stubs do not verify SAP signatures or delivery.');
