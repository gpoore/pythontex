    // -*- coding: utf-8 -*-
    #![allow(dead_code)]
    
    mod rust_tex_utils {
    use std::{fmt, collections};
    use std::io::prelude::*;
    pub struct RustTeXUtils {
        formatter_: Box<FnMut(&fmt::Display) -> String>,
        before_: Box<FnMut()>,
        after_: Box<FnMut()>,
        dependencies: Vec<String>,
        created: Vec<String>,
        command_: &'static str,
        context_: collections::HashMap<&'static str, &'static str>,
        args_: collections::HashMap<&'static str, &'static str>,
        instance_: &'static str,
        line_: &'static str,
    }
    impl RustTeXUtils {
        pub fn new() -> Self {
            RustTeXUtils {
                formatter_: Box::new(|x: &fmt::Display| format!("{}", x)),
                before_: Box::new(|| {}),
                after_: Box::new(|| {}),
                dependencies: Vec::new(),
                created: Vec::new(),
                command_: "",
                context_: collections::HashMap::new(),
                args_: collections::HashMap::new(),
                instance_: "",
                line_: "",
            }
        }
        
        pub fn formatter<A: fmt::Display>(&mut self, x: A) {
            (*self.formatter_)(&x);
        }
        
        pub fn set_formatter<F: FnMut(&fmt::Display) -> String + 'static>(&mut self, f: F) {
            self.formatter_ = Box::new(f);
        }
        
        pub fn before(&mut self) {
            (*self.before_)();
        }
        
        pub fn set_before<F: FnMut() + 'static>(&mut self, f: F) {
            self.before_ = Box::new(f);
        }
        
        pub fn after(&mut self) {
            (*self.after_)();
        }
        
        pub fn set_after<F: FnMut() + 'static>(&mut self, f: F) {
            self.after_ = Box::new(f);
        }
        
        pub fn add_dependencies<SS: IntoIterator>(&mut self, deps: SS) where SS::Item: Into<String> {
            self.dependencies.append(&mut deps.into_iter().map(|x| x.into()).collect());
        }
        
        pub fn add_created<SS: IntoIterator>(&mut self, crts: SS) where SS::Item: Into<String> {
            self.created.append(&mut crts.into_iter().map(|x| x.into()).collect());
        }
        
        pub fn cleanup(self) {
            println!("{}", "");
            for x in self.dependencies {
                println!("{}", x);
            }
            println!("{}", "");
            for x in self.created {
                println!("{}", x);
            }
        }
        
        pub fn family(&self) -> &'static str {
            ""
        }
        
        pub fn session(&self) -> &'static str {
            ""
        }
        
        pub fn restart(&self) -> &'static str {
            ""
        }
        
        pub fn setup_wrapper(mut self, cmd: &'static str, cxt: &'static str, ags: &'static str, ist: &'static str, lne: &'static str) -> Self {
            fn parse_map(kvs: &'static str) -> collections::HashMap<&'static str, &'static str> {
                kvs.split(',').filter(|s| !s.is_empty()).map(|kv| {
                    let (k, v) = kv.split_at(kv.find('=').expect(&format!("Error parsing supposed key-value pair ({})", kv)));
                    (k.trim(), v[1..].trim())
                }).collect()
            }
            self.command_ = cmd;
            self.context_ = parse_map(cxt);
            self.args_ = parse_map(ags);
            self.instance_ = ist;
            self.line_ = lne;
            self
        }
        
        pub fn command(&self) -> &'static str {
            self.command_
        }
        
        pub fn context(&self) -> &collections::HashMap<&'static str, &'static str> {
            &self.context_
        }
        
        pub fn args(&self) -> &collections::HashMap<&'static str, &'static str> {
            &self.args_
        }
        
        pub fn instance(&self) -> &'static str {
            self.instance_
        }
        
        pub fn line(&self) -> &'static str {
            self.line_
        }
    }
    }
    
    use std::{io, env, ffi};
    use std::io::prelude::*;
    #[allow(unused_mut)]
    fn main() {
    let mut rstex = rust_tex_utils::RustTeXUtils::new();
    if env::set_current_dir(ffi::OsString::from("/".to_string())).is_err() && env::args().all(|x| x != "--manual") {
        panic!("Could not change to the specified working directory (/)");
    }
    

    
    let mut rstex = rstex.setup_wrapper("", "", "", "", "");
    println!("");
    writeln!(io::stderr(), "").unwrap();
    rstex.before();
    

    
    rstex.after();
    
    rstex.cleanup()
    }
