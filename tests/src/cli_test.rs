/// test-cli - 子进程，验证虚拟文件系统能否被子进程访问
fn main() {
    let args: Vec<String> = std::env::args().collect();
    print!("子进程 test-cli.exe 启动");
    if args.len() > 1 {
        print!(", 参数: {}", args[1..].join(" "));
    }
    println!();
    println!("子进程当前目录: {}", std::env::current_dir().unwrap().display());
    // 尝试读取主进程创建的 test_output.txt
    let content = std::fs::read_to_string("test_output.txt").unwrap_or_default();
    if !content.is_empty() {
        println!("子进程可读取 test_output.txt: {}", content.trim());
    } else {
        println!("子进程不可读取 test_output.txt（需 ShareVirtualSystem=true）");
    }
}
