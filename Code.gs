//  1. Define sheet names where data is to be written below
var INFLUENCE_SHEET_NAME = "Influence";
         
//  2. Run > setup
//
//  3. Publish > Deploy as web app 
//    - enter Project Version name and click 'Save New Version' 
//    - set security level and enable service (most likely execute as 'me' and access 'anyone, even anonymously) 
//
//  4. Copy the 'Current web app URL' and post this in your form/script action 
//
//  5. Insert column names on your destination sheet matching the parameter names of the data you are passing in (exactly matching case)
 
var SCRIPT_PROP = PropertiesService.getScriptProperties(); // new property service
 
// If you don't want to expose either GET or POST methods you can comment out the appropriate function
function doGet(e){
  return handleResponse(e);
}
 
function doPost(e){
  return handleResponse(e);
}
 
function updateInfluence(doc, e) {
  // store values in the appropriate sheet
  var sheet = doc.getSheetByName(INFLUENCE_SHEET_NAME);
     
  // we'll use headers in row 1 to define attributes to retrieve
  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var nextRow = sheet.getLastRow()+1; // get next row
  var row = [];
  // loop through the header columns, ignoring undefined entries
  for (header in headers){
    if (typeof e.parameter[headers[header]] != "undefined") {
      row.push(e.parameter[headers[header]]);
    }
  }
  // more efficient to set values as [][] array than individually
  sheet.getRange(nextRow, 1, 1, row.length).setValues([row]);  
}

function handleResponse(e) {
  // Confirm this as a valid request before doing anything
  var reqKey = SCRIPT_PROP.getProperty("api_key");
  var specifiedKey = e.parameter["API_KEY"];
  if (specifiedKey != reqKey) {
    // return json invalid credentials results
    return ContentService.createTextOutput(JSON.stringify({"result":"invalid"}))
          .setMimeType(ContentService.MimeType.JSON);
  }

  // prevent concurrent access overwritting data
  // [1] http://googleappsdeveloper.blogspot.co.uk/2011/10/concurrency-and-google-apps-script.html
  // we want a public lock, one that locks for all invocations
  var lock = LockService.getPublicLock();
  lock.waitLock(30000);  // wait 30 seconds before conceding defeat.
   
  try {
    // set where we write the data
    var doc = SpreadsheetApp.openById(SCRIPT_PROP.getProperty("key"));
    // update influence data
    updateInfluence(doc, e);

    // return json success results
    return ContentService
          .createTextOutput(JSON.stringify({"result":"success", "row": nextRow}))
          .setMimeType(ContentService.MimeType.JSON);
  } catch(e){
    // if error return this
    return ContentService
          .createTextOutput(JSON.stringify({"result":"error", "error": e}))
          .setMimeType(ContentService.MimeType.JSON);
  } finally { //release lock
    lock.releaseLock();
  }
}
 
function setup() {
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    SCRIPT_PROP.setProperty("key", doc.getId());
}
