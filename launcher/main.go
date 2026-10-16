package main

import (
	"bufio"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"
)

var (
	crawlerCmd *exec.Cmd
	pythonCmd  *exec.Cmd
)

func main() {
	fmt.Println("=========================================================")
	fmt.Println("   🕷  VAPLERS SEO SPIDER & AUDIT ENGINE LAUNCHER")
	fmt.Println("=========================================================")

	// 1. Determine Project Root directory (where Auditer.exe resides)
	exePath, err := os.Executable()
	if err != nil {
		fmt.Printf("[Error] Failed to get executable path: %v\n", err)
		return
	}
	projectRoot := filepath.Dir(exePath)
	// If run via 'go run', fallback to current working directory
	if _, err := os.Stat(filepath.Join(projectRoot, "main.py")); os.IsNotExist(err) {
		cwd, _ := os.Getwd()
		if _, err := os.Stat(filepath.Join(cwd, "main.py")); err == nil {
			projectRoot = cwd
		}
	}

	fmt.Printf("[Info] Project Root: %s\n", projectRoot)

	// Setup clean shutdown on Ctrl+C or window close
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sigChan
		fmt.Println("\n[Shutdown] Stopping services...")
		cleanup()
		os.Exit(0)
	}()

	// 2. Locate Python executable
	pythonExe := findPython(projectRoot)
	if pythonExe == "" {
		fmt.Println("[Error] Python executable not found. Please install Python or set up .venv.")
		pressEnterToExit()
		return
	}
	fmt.Printf("[Info] Using Python: %s\n", pythonExe)

	// 3. Ensure React Frontend is built
	frontendDist := filepath.Join(projectRoot, "frontend", "dist")
	if _, err := os.Stat(frontendDist); os.IsNotExist(err) {
		frontendDir := filepath.Join(projectRoot, "frontend")
		if _, err := os.Stat(frontendDir); err == nil {
			fmt.Println("[Build] Compiling React Frontend (Vite + Zustand + TanStack Virtual)...")
			npmCmd := exec.Command("cmd", "/c", "npm run build")
			npmCmd.Dir = frontendDir
			npmCmd.Stdout = os.Stdout
			npmCmd.Stderr = os.Stderr
			if err := npmCmd.Run(); err != nil {
				fmt.Printf("[Warning] Frontend build notice: %v\n", err)
			}
		}
	}

	// 4. Check & Start Go Crawler Service on :50051
	goBin := filepath.Join(projectRoot, "go-crawler", "bin", "crawler.exe")
	if _, err := os.Stat(goBin); os.IsNotExist(err) {
		fmt.Println("[Build] Compiling Go High-Throughput Crawler engine...")
		buildGo := exec.Command("cmd", "/c", "go build -o bin\\crawler.exe .\\cmd\\crawler")
		buildGo.Dir = filepath.Join(projectRoot, "go-crawler")
		buildGo.Stdout = os.Stdout
		buildGo.Stderr = os.Stderr
		if err := buildGo.Run(); err != nil {
			fmt.Printf("[Warning] Go crawler compilation notice: %v\n", err)
		}
	}

	if !isPortOpen(50051) {
		if _, err := os.Stat(goBin); err == nil {
			fmt.Println("[Service] Starting Go High-Throughput Engine on port 50051...")
			crawlerCmd = exec.Command(goBin, "--port=50051")
			crawlerCmd.Dir = projectRoot
			if err := crawlerCmd.Start(); err != nil {
				fmt.Printf("[Warning] Failed to start Go crawler: %v\n", err)
			}
		}
	} else {
		fmt.Println("[Service] Go Crawl Engine already active on port 50051.")
	}

	// 5. Start Python Web Backend
	fmt.Println("[Service] Starting Web Application on http://localhost:8000 ...")
	mainPy := filepath.Join(projectRoot, "main.py")
	pythonCmd = exec.Command(pythonExe, mainPy)
	pythonCmd.Dir = projectRoot
	pythonCmd.Stdout = os.Stdout
	pythonCmd.Stderr = os.Stderr

	if err := pythonCmd.Start(); err != nil {
		fmt.Printf("[Error] Failed to start Python server: %v\n", err)
		cleanup()
		pressEnterToExit()
		return
	}

	// 6. Wait for Web Server to be ready, then open Browser
	go func() {
		if waitForServer("http://localhost:8000", 15*time.Second) {
			fmt.Println("[Browser] Opening http://localhost:8000 in your default browser...")
			time.Sleep(400 * time.Millisecond)
			openBrowser("http://localhost:8000")
		} else {
			fmt.Println("[Warning] Web server took longer to respond. You can open http://localhost:8000 manually.")
		}
	}()

	fmt.Println("\n[Ready] Application running! Press Ctrl+C in this window to stop both services.\n")

	// Wait for Python server process
	if err := pythonCmd.Wait(); err != nil {
		fmt.Printf("[Info] Web server exited: %v\n", err)
	}

	cleanup()
}

func findPython(root string) string {
	venvPy := filepath.Join(root, ".venv", "Scripts", "python.exe")
	if _, err := os.Stat(venvPy); err == nil {
		return venvPy
	}
	cachePy := `C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
	if _, err := os.Stat(cachePy); err == nil {
		return cachePy
	}
	if path, err := exec.LookPath("python"); err == nil {
		return path
	}
	return ""
}

func isPortOpen(port int) bool {
	conn, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", port), 400*time.Millisecond)
	if err == nil {
		conn.Close()
		return true
	}
	return false
}

func waitForServer(url string, timeout time.Duration) bool {
	deadline := time.Now().Add(timeout)
	client := http.Client{Timeout: 1 * time.Second}
	for time.Now().Before(deadline) {
		resp, err := client.Get(url)
		if err == nil {
			resp.Body.Close()
			return true
		}
		time.Sleep(350 * time.Millisecond)
	}
	return false
}

func openBrowser(url string) {
	exec.Command("rundll32", "url.dll,FileProtocolHandler", url).Start()
}

func cleanup() {
	if pythonCmd != nil && pythonCmd.Process != nil {
		exec.Command("taskkill", "/F", "/T", "/PID", fmt.Sprintf("%d", pythonCmd.Process.Pid)).Run()
	}
	if crawlerCmd != nil && crawlerCmd.Process != nil {
		exec.Command("taskkill", "/F", "/T", "/PID", fmt.Sprintf("%d", crawlerCmd.Process.Pid)).Run()
	}
}

func pressEnterToExit() {
	fmt.Println("\nPress Enter to exit...")
	bufio.NewReader(os.Stdin).ReadBytes('\n')
}

