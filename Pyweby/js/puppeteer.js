
// usage:
// step1: git clone https://github.com/GoogleChrome/puppeteer.git
// step2: npm i puppeteer [use `npm config set puppeteer_download_host=https://npm.taobao.org/mirrors` npm source for downloading headless chrome]
// requires: npm i mysql
// step3: create table: create table vluns (id INT NOT NULL AUTO_INCREMENT,title varchar(100),serial varchar(100),time varchar(100),component varchar(100),cve varchar(100),type varchar(100),PRIMARY KEY(id))engine=InnoDB DEFAULT CHARSET =utf8;
// step4: node file.js to start project.


//problem: chrome could not launch by missing .so on Debian
//visit : https://packages.debian.org/search?mode=path&suite=sid&section=all&arch=any&searchon=contents&keywords=libatk-bridge-2.0.so.0
//search and install missing library.

const puppeteer = require('puppeteer');
var util = require('util');

//using mysql
//var mysql      = require('mysql');
//var connection = mysql.createConnection({
//  host     : 'localhost',
//  user     : 'root',
//  password : '787518771',
//  database : 'test'
//});
//connection.connect();
//var  addSql = 'INSERT INTO vluns(id,title,serial,time,component,cve,type) VALUES(0,?,?,?,?,?,?)';


//using mongodb
//mongodb usage: version>2.6 required
//curl -O https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-3.0.6.tgz
//tar -zxvf mongodb-linux-x86_64-3.0.6.tgz
//mv  mongodb-linux-x86_64-3.0.6/ /usr/local/mongodb
//cd /usr/local/mongodb/bin
//mkdir -p /data/db
//nohup ./mongod &
//export PATH=$PWD:$PATH
var MongoClient = require('mongodb').MongoClient;
var url = "mongodb://localhost:27017/vluns";


process.setMaxListeners(0);  //MaxListenersExceededWarning: Possible EventEmitter memory leak detected

let scrape = async() => {
        var retry_max = 0;
        var retry_max_2 = 0;
        var flag_max = 0;

        for(let p=1;p<=2837;p++){

            for(let i=1; i<=20; i++){

                console.log("index:",p,i);
                // Error: WebSocket is not open: readyState 2 (CLOSING) . DO not set const browser out of cycle.
                const browser = await puppeteer.launch({headless:true, args: ['--no-sandbox', '--disable-setuid-sandbox']});
                const page = await browser.newPage();
                var pager = util.format('https://www.seebug.org/vuldb/vulnerabilities?page=%s',p);
                try{
                    await page.goto(pager);   //UnhandledPromiseRejectionWarning: Error: net::ERR_CONNECTION_RESET
                    await page.waitForNavigation({waitUntil:['load','domcontentloaded'],timeout:20000});
                    retry_max = 0;
                    //load - consider navigation to be finished when the load event is fired.
                    //domcontentloaded - consider navigation to be finished when the DOMContentLoaded event is fired.
                    //networkidle0 - consider navigation to be finished when there are no more than 0 network connections for at least 500 ms.
                    //networkidle2 - consider navigation to be finished when there are no more than 2 network connections for at least 500 ms.
                }catch(e){
                    // throw timeout exception
                    retry_max += 1;
                    if (retry_max > 3){
                        retry_max = 0;
                        await browser.close();
                        continue;
                    }
                    i -= 1;
                    await browser.close();   //Error: Execution context was destroyed, most likely because of a navigation.? Solved?
                    continue;
                }

                await page.waitFor(800);
                // 格式化css选择器
                var clicker = util.format('body > div.container > div > div > div > div > table > tbody > tr:nth-child(%s) > td.vul-title-wrapper > a',i);
                try{
                    await page.click(clicker);
                    flag_max = 0;
                }catch(e){
                    flag_max += 1;
                    if(flag_max>3){
                        flag_max = 0;
                        console.log("retry max. go next...");
                        await browser.close();   //Error: Execution context was destroyed, most likely because of a navigation.? Solved?
                        continue;
                    }
                    i-=1;   //for error click, scroll back and redo this again.
                    console.log("retry:",flag_max);
                    await browser.close();
                    continue;
                }


                //await page.waitForNavigation(['networkidle0', 'load', 'domcontentloaded']);  //Error: Execution context was destroyed, most likely because of a navigation.? Solved?
                try{
                    await page.waitForNavigation({waitUntil:['load','domcontentloaded'],timeout:20000});
                    retry_max_2 = 0;
                }catch(e){
                    retry_max_2 += 1;
                    if(retry_max_2 > 3){
                        retry_max_2 = 0;
                        await browser.close();
                        continue;
                    }
                    i-=1;
                    await browser.close();
                    continue;
                }

                await page.waitFor(800);

                const result = await page.evaluate(async () => {
                    try{

                        let serial = document.querySelector('#j-vul-basic-info > div > div:nth-child(1) > dl:nth-child(1) > dd > a').innerText.trim();
                        let time = document.querySelector('#j-vul-basic-info > div > div:nth-child(1) > dl:nth-child(3) > dd').innerHTML.trim();
                        let component = document.querySelector('#j-vul-basic-info > div > div:nth-child(2) > dl:nth-child(2) > dd > a').innerText.trim();
                        let cve = document.querySelector('#j-vul-basic-info > div > div:nth-child(3) > dl:nth-child(1) > dd > a').getAttribute('href').trim();
                        let title = document.querySelector('#j-vul-title > span').innerText;
                        let type = document.querySelector('#j-vul-basic-info > div > div:nth-child(2) > dl:nth-child(1) > dd > a').innerText.trim();
                        return {title,serial,time,component,cve,type};
                       } catch(e){
                            // await page.waitFor(2000); SyntaxError: await is only valid in async function
                            // if return result, odd to raise Error:
                            // UnhandledPromiseRejectionWarning: Error: Evaluation failed: ReferenceError: result is not defined
                            setTimeout(function(){console.log("some error.continue")},3000);
                            return null;
                       }
                });

                if(result){
                    console.log(result.title)
                    if(Object.keys(result).length>0){

                        //use mysql
//                        var  addSqlParams = [result.title, result.browser,result.time, result.component,result.cve,result.type];
//                        connection.query(addSql,addSqlParams,function (err, result) {
//                            if(err){
//                                console.log('error insert!');
//                            }
//                        });


                        //use mongodb
                         MongoClient.connect(url,{ useNewUrlParser: true }, function(err, db) {
                            if (err) throw err;
                            var dbo = db.db("vluns");
                            dbo.collection("seebug").insertOne(result, function(err, res) {
                                if (err) throw err;
                                db.close();
                            });
                        });

                    }

                }

                // when use browser.close() rather than await . may cause error like below:
                // Error: Protocol error (Target.createTarget): Target closed.
                // reason:
                // The only usage of Target.createTarget in Puppeteer is in browser.newPage().
                // This error would happen if you call browser.close() while browser.newPage()
                // reference: https://github.com/GoogleChrome/puppeteer/issues/1947
                await browser.close();
            }
        }
};

scrape().then((value) => {
        console.log("Done.");
});

