/// Test App - 主程序，验证 EVB 打包后的各种功能
use std::env;
use std::fs;
use std::process::Command;

fn main() {
    println!("=== EVB 测试应用 ===");
    println!("exe 路径: {}", env::current_exe().unwrap().display());
    println!("当前目录: {}", env::current_dir().unwrap().display());

    // Test 1: 读取配套的 config.json
    match fs::read_to_string("config.json") {
        Ok(content) => println!("config.json 存在: {} 字节, 内容: {}", content.len(), content.trim()),
        Err(_) => println!("config.json 不存在"),
    }

    // Test 2: 写入外部文件（测试虚拟文件系统下写入是否可持久化）
    fs::write("test_output.txt", "EVB 测试写入成功\n").ok();
    println!("test_output.txt 已写入");

    // Test 3: 验证嵌入的二进制数据
    match fs::metadata("data.bin") {
        Ok(meta) => println!("data.bin 存在: {} KB", meta.len() / 1024),
        Err(_) => println!("data.bin 不存在"),
    }

    // Test 4: 调用子进程（测试 ShareVirtualSystem）
    let child = Command::new("test-cli.exe").arg("--hello").output();
    match child {
        Ok(output) => {
            let out = String::from_utf8_lossy(&output.stdout);
            println!("子进程 test-cli.exe: {}", out.trim());
        }
        Err(e) => {
            println!("子进程 test-cli.exe 调用失败: {}", e);
        }
    }

    println!("=== 测试结束 ===");
}
