use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, ensure};
use clap::{Parser, Subcommand};
use sbgn_libavoid::{RoutingConfig, SbgnDocument, bend_count};

#[derive(Debug, Parser)]
#[command(about = "Route SBGN arcs orthogonally without moving glyphs")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Route one SBGN file or every .sbgn file in a directory.
    Route {
        /// Input SBGN file or flat directory.
        #[arg(short, long)]
        input: PathBuf,
        /// Output file or directory.
        #[arg(short, long)]
        output: PathBuf,
        /// Clearance between routes and non-container glyphs.
        #[arg(long, default_value_t = 4.0)]
        shape_buffer_distance: f64,
        /// Preferred distance between nudged parallel routes.
        #[arg(long, default_value_t = 4.0)]
        ideal_nudging_distance: f64,
        /// Penalty for additional route segments.
        #[arg(long, default_value_t = 10.0)]
        segment_penalty: f64,
        /// Penalty for connector crossings.
        #[arg(long, default_value_t = 200.0)]
        crossing_penalty: f64,
    },
}

fn collect_inputs(input: &Path) -> Result<Vec<PathBuf>> {
    if input.is_file() {
        ensure!(
            input.extension().and_then(|value| value.to_str()) == Some("sbgn"),
            "input file must end in .sbgn"
        );
        return Ok(vec![input.to_path_buf()]);
    }
    ensure!(input.is_dir(), "input does not exist: {}", input.display());
    let mut paths = fs::read_dir(input)
        .with_context(|| format!("failed to read {}", input.display()))?
        .filter_map(|entry| entry.ok().map(|entry| entry.path()))
        .filter(|path| path.extension().and_then(|value| value.to_str()) == Some("sbgn"))
        .collect::<Vec<_>>();
    paths.sort();
    ensure!(
        !paths.is_empty(),
        "no .sbgn files found in {}",
        input.display()
    );
    Ok(paths)
}

fn output_path(input: &Path, output: &Path, multiple: bool) -> Result<PathBuf> {
    if multiple || output.is_dir() || output.extension().is_none() {
        let filename = input
            .file_name()
            .context("input path does not contain a filename")?;
        Ok(output.join(filename))
    } else {
        Ok(output.to_path_buf())
    }
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Command::Route {
            input,
            output,
            shape_buffer_distance,
            ideal_nudging_distance,
            segment_penalty,
            crossing_penalty,
        } => {
            let config = RoutingConfig {
                shape_buffer_distance,
                ideal_nudging_distance,
                segment_penalty,
                crossing_penalty,
            };
            let inputs = collect_inputs(&input)?;
            let multiple = inputs.len() > 1 || input.is_dir();
            for input_path in &inputs {
                let destination = output_path(input_path, &output, multiple)?;
                let mut document = SbgnDocument::read(input_path)?;
                let node_count = document.graph().nodes.len();
                let edge_count = document.graph().edges.len();
                let routes = document.route_arcs(&config)?;
                document.write(&destination)?;
                println!(
                    "{}\tnodes={}\tarcs={}\tbends={}\t{}",
                    input_path.display(),
                    node_count,
                    edge_count,
                    bend_count(&routes),
                    destination.display()
                );
            }
        }
    }
    Ok(())
}
